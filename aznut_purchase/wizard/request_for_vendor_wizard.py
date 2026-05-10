from odoo import fields, models, api

from werkzeug.urls import url_join

from ..models.purchase_order import get_mail_compose_message_action


class RequestForVendorWizard(models.TransientModel):
    _name = 'request.for.vendor.wizard'
    _description = 'Request For Vendor Wizard'

    request_for_vendor_wizard_line_ids = fields.One2many(
        'request.for.vendor.wizard.line',
        'request_for_vendor_wizard_id',
        string='Request For Vendor Wizard Lines',
        readonly=True,
    )
    show_button_reset = fields.Boolean(
        string='Show Reset Button',
        compute='_compute_show_buttons',
    )
    show_include_all_button = fields.Boolean(
        string='Show Include All Button',
        compute='_compute_show_buttons',
    )

    @api.depends('request_for_vendor_wizard_line_ids.included_in_email')
    def _compute_show_buttons(self):
        self.show_button_reset, self.show_include_all_button = False, False
        for wizard in self:
            if True in wizard.mapped('request_for_vendor_wizard_line_ids.included_in_email'):
                wizard.show_button_reset = True
            if False in wizard.mapped('request_for_vendor_wizard_line_ids.included_in_email'):
                wizard.show_include_all_button = True

    def action_confirm(self):
        self.ensure_one()
        for wizard_line in self.request_for_vendor_wizard_line_ids.filtered(lambda ln: ln.included_in_email):
            wizard_line._compute_email_template()
            mail_compose_message = self.env['mail.compose.message'].browse(
                get_mail_compose_message_action(self, 'Request For Vendor', wizard_line.partner_id.ids,
                                                wizard_line.email_template, wizard_line.order_id.id, 'purchase.order',
                                                '%s Request For Vendor' % wizard_line.order_id.name or 'No Order').get(
                    'res_id'))
            mail_compose_message.action_send_mail()
        return {'type': 'ir.actions.act_window_close'}

    def action_include_all(self):
        self.ensure_one()
        self.request_for_vendor_wizard_line_ids.write({'included_in_email': True})
        return self.env['request.for.vendor.wizard'].get_wizard_action(self)

    def action_reset(self):
        self.ensure_one()
        self.request_for_vendor_wizard_line_ids.write({'included_in_email': False})
        return self.env['request.for.vendor.wizard'].get_wizard_action(self)

    def get_wizard_action(self, request_for_vendor_wizard):
        return {
            'name': 'Request For Vendor',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'request.for.vendor.wizard',
            'view_id': self.env.ref('aznut_purchase.request_for_vendor_wizard_form').id,
            'target': 'new',
            'res_id': request_for_vendor_wizard.id,
        }


class RequestForVendorWizardLine(models.TransientModel):
    _name = 'request.for.vendor.wizard.line'
    _description = 'Request For Vendor Wizard Line'

    request_for_vendor_wizard_id = fields.Many2one(
        'request.for.vendor.wizard',
        string='Request For Vendor Wizard',
    )
    order_id = fields.Many2one(
        'purchase.order',
        store=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        related='order_id.partner_id',
    )
    date_planned = fields.Datetime(
        related='order_id.date_planned',
    )
    included_in_email = fields.Boolean(
        string='Included In Email',
    )
    email_template = fields.Html(
        string='Email Template',
        store=False,
        compute='_compute_email_template',
    )
    order_link = fields.Char(
        string='Order Link',
        compute='_compute_order_link',
    )

    @api.depends('order_id')
    def _compute_order_link(self):
        menu_id = self.env.ref('purchase.menu_purchase_root').id
        action_id = self.env.ref('purchase.purchase_form_action').id

        for wizard_line in self:
            secondary_url = 'web#id=%s&menu_id=%s&action=%s&model=purchase.order&view_type=form' % (
                wizard_line.order_id.id, menu_id, action_id
            )
            wizard_line.order_link = url_join(wizard_line.get_base_url(), secondary_url)

    def _compute_email_template(self):
        param = self.env['ir.config_parameter'].sudo()
        body = param.get_param('aznut_purchase.request_for_vendor_email_template') or ''
        self.email_template = ''
        for wizard_line in self:
            if '%name%' in body:
                body = body.replace('%name%', wizard_line.order_id.partner_id.name or '')
            if '%link%' in body:
                link = url_join(wizard_line.get_base_url(),
                                'request_for_vendor?request_for_vendor_access_token=%s' % wizard_line.order_id.request_for_vendor_access_token)
                body = body.replace('%link%', link or '')
            wizard_line.email_template = body

    def action_include_in_email(self):
        self.ensure_one()
        self.included_in_email = True
        return self.env['request.for.vendor.wizard'].get_wizard_action(self.request_for_vendor_wizard_id)

    def action_exclude_from_email(self):
        self.ensure_one()
        self.included_in_email = False
        return self.env['request.for.vendor.wizard'].get_wizard_action(self.request_for_vendor_wizard_id)
