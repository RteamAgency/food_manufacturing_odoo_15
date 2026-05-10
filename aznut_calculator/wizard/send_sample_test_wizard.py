from odoo import fields, models


class SendSampleTestWizard(models.TransientModel):
    _name = 'send.sample.test.wizard'
    _description = 'Send Sample Test Wizard'

    sample_test_order_id = fields.Many2one(
        'mrp.production',
        string='Sample Test Orders',
        required=True,
    )
    allowed_sample_test_orders_ids = fields.Many2many(
        'mrp.production',
        'allowed_sample_test_orders_rel',
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        required=True,
    )

    def action_send(self):
        self.ensure_one()

        template_id = self.env['ir.model.data']._xmlid_to_res_id('aznut_calculator.sample_test_email',
                                                                 raise_if_not_found=False)
        ctx = {
            'default_model': 'mrp.production',
            'default_res_id': self.sample_test_order_id.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_pa'
            'default_composition_mode': 'comment',
            'mark_as_sent': True,
            'custom_layout': "mail.mail_notification_light",
            'force_email': True,
            'default_partner_ids': self.partner_id.ids,
            'lead_message_copy': True,
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
