from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _action_send_mail(self, auto_commit=False):
        res = super(MailComposeMessage, self)._action_send_mail(auto_commit=auto_commit)
        if self.model == 'purchase.order':
            order = self.env['purchase.order'].browse(self.res_id)
            if self.env.context.get('availability_confirmation_mail'):
                order.write({
                    'supplier_mails_state': 'availability_confirmation_mail_sent',
                    'supplier_confirmation_status': 'waiting_for_confirmation',
                })
            elif self.env.context.get('shipping_information_request_mail'):
                order.write({
                    'supplier_mails_state': 'shipping_information_request_mail_sent',
                })
            elif self.env.context.get('confirmation_to_supplier_mail'):
                order.write({
                    'supplier_mails_state': 'confirmation_to_supplier_mail_send',
                })
        return res
