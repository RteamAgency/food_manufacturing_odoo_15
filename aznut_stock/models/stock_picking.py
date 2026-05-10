from odoo import fields, models, api
import json
import base64


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    stock_source_tags = fields.Char(
        compute="_compute_stock_tags"
    )
    can_report_send = fields.Boolean(
        string="Can Report Send",
        compute="_compute_can_report_send"
    )
    reserved_from_stock = fields.Boolean(
        string='Reserved From Stock',
        compute='_compute_reserved_from_stock'
    )

    def do_unreserve(self):
        res = super(StockPicking, self).do_unreserve()
        self.move_line_ids.write({'reserved_from_stock': False})
        return res

    @api.depends('move_line_ids.reserved_from_stock')
    def _compute_reserved_from_stock(self):
        self.reserved_from_stock = False
        for picking in self:
            if picking.move_line_ids.filtered(lambda ml: ml.reserved_from_stock):
                picking.reserved_from_stock = True

    @api.depends('picking_type_id')
    def _compute_can_report_send(self):
        allowed_types = ['Store Finished Product', 'Delivery Orders']
        for rec in self:
            if rec.picking_type_id.name in allowed_types:
                rec.can_report_send = True
            else:
                rec.can_report_send = False

    def _compute_stock_tags(self):
        for rec in self:
            tags = []
            if rec.purchase_id and rec.purchase_id.origin:
                tags.append(rec.purchase_id.origin)
            elif rec.sale_id and rec.sale_id.tag_ids:
                tags = rec.sale_id.tag_ids.mapped('name')
            else:
                tags.append("")
            rec.stock_source_tags = json.dumps(tags)

    def action_send_transfer_report(self):
        self.ensure_one()
        if self.picking_type_code == 'outgoing':
            return self.send_delivery_transfer_report()
        if self.picking_type_code == 'internal':
            return self.send_store_transfer_report()

    def _create_report_attachment(self, file, model, name, encode=None):
        data_record = base64.b64encode(file) if not encode else file
        ir_values = {
            'name': name,
            'type': 'binary',
            'datas': data_record,
            'store_fname': data_record,
            'mimetype': 'application/pdf',
            'res_model': model,
        }
        return self.env['ir.attachment'].sudo().create(ir_values)

    def get_composer_values(self, attachment_ids, mail_template):
        ctx = {
            'default_model': 'stock.picking',
            'default_res_id': self.ids[0],
            'default_use_template': bool(mail_template),
            'default_template_id': mail_template.id,
            'default_composition_mode': 'comment',
            'mark_as_sent': True,
            'custom_layout': "mail.mail_notification_light",
            'force_email': True,
            'default_attachment_ids': attachment_ids
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def send_delivery_transfer_report(self):
        mail_template = self.env.ref('aznut_stock.aznut_delivery_transfer_email')
        slip_template = self.env.ref('stock.action_report_delivery')
        check_template = self.env.ref('quality_control.quality_check_report')
        check_pdf = check_template._render_qweb_pdf(self.check_ids.ids)[0]
        slip_pdf = slip_template._render_qweb_pdf([self.id])[0]
        slip_filename = f'Delivery Slip - {self.partner_id.display_name} - {self.name}'
        check_filename = 'Worksheet Report - External (PDF)'
        attachments = [
            self._create_report_attachment(check_pdf, 'quality.check', check_filename),
            self._create_report_attachment(slip_pdf, 'stock.picking', slip_filename),
        ]
        attachment_ids = [attachment.id for attachment in attachments]
        return self.get_composer_values(attachment_ids, mail_template)

    def send_store_transfer_report(self):
        production_id = self.group_id.mrp_production_ids
        if production_id:
            attachments = []
            for check in self.check_ids:
                check_template = check.worksheet_template_id.model_id.model
                quality_worksheet = self.env[check_template].search([('x_quality_check_id', '=', check.id)])
                laboratory_test = quality_worksheet.x_studio_add_laboratory_test
                laboratory_test_filename = quality_worksheet.x_studio_add_laboratory_test_filename
                if laboratory_test:
                    attachments.append(self._create_report_attachment(laboratory_test, 'mrp.production', laboratory_test_filename, True))
            mail_template = self.env.ref('aznut_stock.aznut_store_product_email')
            productionn_tempalate = self.env.ref('mrp.action_report_production_order')
            productionn_pdf = productionn_tempalate._render_qweb_pdf([production_id.id])[0]
            filename = f'Production Order - {self.origin}'
            attachments.append(self._create_report_attachment(productionn_pdf, 'mrp.production', filename))
            attachment_ids = [attachment.id for attachment in attachments]
            return self.get_composer_values(attachment_ids, mail_template)
