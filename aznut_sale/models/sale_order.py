################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2019 SmartTek (<https://smartteksas.com/>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
################################################################################

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import base64


class SaleOrder(models.Model):
    _inherit = "sale.order"

    name = fields.Char(
        compute='_compute_name',
        store=True,
    )
    ordered_qty = fields.Float(
        string='Ordered',
        compute='_compute_so_qty',
    )
    free_qty = fields.Float(
        string='Free On Hand',
        compute='_compute_so_qty',
    )
    manufactured_qty = fields.Float(
        string='Manufactured',
        compute='_compute_so_qty',
        store="True"
    )
    delivered_qty = fields.Float(
        string='Shipped',
        compute='_compute_so_qty',
    )
    remaining_qty = fields.Float(
        string='To Ship',
        compute='_compute_so_qty',
    )
    real_manufactured_qty = fields.Float(
        string='Actual Manufactured',
        compute='_compute_so_qty',
    )
    payment_status = fields.Selection(
        [('paid', 'Fully Paid'),
         ('partially_paid', 'Partially Paid'),
         ('waiting', 'Waiting For Payment')],
        default='waiting',
        string='Payment Status',
        required=True,
        copy=False,
    )
    manufacture_scheduled_date = fields.Datetime(
        string='Manufacture Scheduled Date',
        compute='_compute_so_qty',
    )
    show_lines_reserve_button = fields.Boolean(
        string='Show Lines Reserve Button',
        compute='_compute_show_lines_reserve_button',
    )
    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_is_overdue',
    )

    @api.depends('order_line.product_id.attribute_line_ids.value_ids', 'state')
    def _compute_name(self):
        for so in self.filtered(lambda rec: rec.state == 'draft'):
            letter = so.name[:1]
            if so.order_line:
                line = min(so.order_line)
                attrs = line.product_id.attribute_line_ids
                attr = attrs.filtered(lambda rec: rec.attribute_id.name == 'Brand')[:1]
                brand = attr.value_ids[:1]
                so.name = so.name.replace(letter, brand.name[:1]) if brand.name else so.name.replace(letter, 'S')
            else:
                so.name = so.name.replace(letter, 'S')

    def _compute_so_qty(self):
        self = self.sudo()
        data = self.env['procurement.group'].read_group([('sale_id', 'in', self.ids)], ['ids:array_agg(id)'],
                                                        ['sale_id'])
        mrp_dict = dict()
        for item in data:
            procurement_groups = self.env['procurement.group'].browse(item['ids'])
            mrp_dict[item['sale_id'][0]] = \
                procurement_groups.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids \
                | procurement_groups.mrp_production_ids

        self.manufacture_scheduled_date = False
        for so in self:
            so.real_manufactured_qty = sum(so.mapped('order_line.real_manufactured_qty'))
            mo_ids = mrp_dict.get(so.id, self.env['mrp.production'])

            so.manufacture_scheduled_date = mo_ids[:1].date_planned_start
            so.ordered_qty = sum(so.order_line.mapped('product_uom_qty'))
            so.free_qty = sum(so.mapped('order_line.available_qty'))
            so.delivered_qty = sum(
                so.picking_ids.filtered(
                    lambda
                        rec: rec.state == 'done' and rec.picking_type_id.code == 'outgoing').move_line_ids_without_package.mapped(
                    'qty_done'))
            so.remaining_qty = so.ordered_qty - so.delivered_qty
            so.manufactured_qty = sum(mo_ids.filtered(lambda mo: mo.state == 'done').mapped('qty_producing'))

    def _compute_show_lines_reserve_button(self):
        self.show_lines_reserve_button = False
        for so in self:
            if so.picking_ids.filtered(lambda picking: picking.state not in ['draft', 'done', 'cancel']):
                so.show_lines_reserve_button = True

    def _compute_is_overdue(self):
        overdue_orders = self.filtered(lambda order: any(pick.is_overdue for pick in order.picking_ids))
        else_orders = self - overdue_orders
        overdue_orders.is_overdue, else_orders.is_overdue = True, False

    def action_confirm(self):
        so = super(SaleOrder, self).action_confirm()
        invalid_lines = self.order_line.filtered(lambda rec: rec.batch > 1 and not rec.product_uom_qty % rec.batch == 0)
        if invalid_lines:
            raise ValidationError(
                _(f'You need to provide value that can be multiplied by batch {", ".join(invalid_lines.mapped("display_name"))}'))
        return so

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        if vals.get('payment_status') and self._check_payment_state(res):
            res._send_payment_state_message()
        return res

    def write(self, values):
        rec = super(SaleOrder, self).write(values)
        if values.get('payment_status') and self._check_payment_state(self):
            self._send_payment_state_message()
        return rec

    def _send_payment_state_message(self):
        for rec in self:
            email_from = (self.env.company.partner_id.email_formatted
                          or self.env.user.email_formatted
                          or self.env.ref('base.user_root').email_formatted)
            mail_values = {
                'auto_delete': False,
                'author_id': self.env.user.partner_id.id,
                'model': 'sale.order',
                'res_id': rec.id,
                'email_from': email_from,
                'email_to': 'orders@bpwlab.com',
                'body_html': f'Order {rec.name} can be started for production.',
                'subject': f'Order {rec.name} can be started for production.',
                'reply_to': '',
            }
            mail_id = self.env['mail.mail'].sudo().create(mail_values)
            mail_id.sudo().send()

    @staticmethod
    def _check_payment_state(so):
        if so.payment_status == 'paid':
            return True
        return False

    def _create_report_attachment(self, file, model, name, encode=None):
        data_record = base64.b64encode(file) if not encode else file
        values = {
            'name': f'Production Order - {name}',
            'type': 'binary',
            'datas': data_record,
            'store_fname': data_record,
            'mimetype': 'application/pdf',
            'res_model': model,
        }
        return self.env['ir.attachment'].sudo().create(values)

    def action_send_report_to_customer(self):
        self.ensure_one()
        attachment = self.env['ir.attachment'].search(
            [('res_id', '=', self.id), ('res_model', '=', 'sale.order'), ('name', 'like', 'wo')],
            order='create_date desc', limit=1)
        procurement_groups = self.env['procurement.group'].search([('sale_id', 'in', self.ids)])
        mrp_production_ids = set(
            procurement_groups.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids.ids) | \
                             set(procurement_groups.mrp_production_ids.ids)
        if mrp_production_ids:
            report_template = self.env.ref('mrp.action_report_production_order')
            production_ids = self.env['mrp.production'].browse(list(mrp_production_ids))
            for rec in production_ids:
                production_pdf = report_template._render_qweb_pdf([rec.id])[0]
                attachment |= self._create_report_attachment(production_pdf, 'mrp.production', rec.name)
        return {
            'name': _('Customer Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_template_id': self.env.ref('aznut_sale.customer_report_mail').id,
                'default_attachment_ids': attachment.ids,
                'default_partner_ids': self.partner_id.ids,
            }
        }


class SaleOrdeLine(models.Model):
    _inherit = "sale.order.line"

    number_of_batches = fields.Integer(
        string='Batches',
        readonly=True,
        store=False,
        compute='_compute_number_of_batches',
    )
    batch = fields.Integer(
        string='Batch',
        related='product_id.batch',
    )
    free_qty = fields.Float(
        related='product_id.free_qty',
        string='Free On Hand',
    )
    reserved_qty = fields.Float(
        string='Reserved Quantity',
        compute='_compute_reserved_qty',
    )
    real_manufactured_qty = fields.Float(
        string='Actual Manufactured',
        compute='_compute_real_manufactured_qty',
    )
    available_qty = fields.Float(
        string='Actual Manufactured',
        compute='_compute_available_qty',
    )

    @api.depends('product_uom_qty')
    def _compute_number_of_batches(self):
        self.number_of_batches = 0
        for line in self:
            if line.batch >= 1 and line.product_uom_qty >= 0:
                if not (line.product_uom_qty % line.batch):
                    line.number_of_batches = line.product_uom_qty / line.batch
                else:
                    line.number_of_batches = 0

    def action_reserve(self):
        self.move_ids._action_assign()

    @api.depends('move_ids.move_line_ids.product_qty')
    def _compute_reserved_qty(self):
        for sol in self:
            sol.reserved_qty = sum(sol.move_ids.mapped('reserved_availability'))

    @api.depends('product_id')
    def _compute_available_qty(self):
        for line in self:
            groups = self.env['procurement.group'].search([('sale_id', '=', line.order_id.id)])
            mo_ids = (
                    groups.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids | groups.mrp_production_ids).filtered(
                lambda mo: mo.product_id.id == line.product_id.id)
            manufactured_qty = sum(mo_ids.filtered(lambda mo: mo.state == 'done').mapped('qty_producing'))
            shipped_qty = line.qty_delivered
            line.available_qty = manufactured_qty - shipped_qty if manufactured_qty > shipped_qty else 0

    def _compute_real_manufactured_qty(self):
        for line in self:
            moves = line.move_ids.filtered(lambda mv: mv.picking_code == 'outgoing')
            done_moves = moves.filtered(lambda mv: mv.picking_id.state == 'done')
            else_moves = moves - done_moves
            line.real_manufactured_qty = sum(done_moves.mapped('move_line_ids.qty_done')) + sum(
                else_moves.mapped('move_line_ids.product_uom_qty'))
