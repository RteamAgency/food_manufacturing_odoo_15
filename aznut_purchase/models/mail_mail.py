from odoo import models


class MailMail(models.Model):
    _inherit = 'mail.mail'

    def _check_seven_days_notice(self):
        for mail in self:
            message = mail.mail_message_id
            if message.model == 'purchase.order' and message.res_id:
                po = self.env['purchase.order'].sudo().browse(message.res_id)
                if (po.partner_id.id in mail.partner_ids.ids + mail.notified_partner_ids.ids or (po.partner_id.email and po.partner_id.email in (
                        mail.email_to or ''))):
                    po.sudo().write({'seven_days_notice': 'red'})

    def send(self, auto_commit=False, raise_exception=False):
        self._check_seven_days_notice()
        res = super(MailMail, self).send(auto_commit, raise_exception)
        return res
