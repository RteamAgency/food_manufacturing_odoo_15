from odoo import models, api


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, vals):
        message = super(MailMessage, self).create(vals)
        if message.model == 'purchase.order' and message.res_id:
            po = self.env['purchase.order'].sudo().browse(message.res_id)
            if (po and po.partner_id.email and po.partner_id.email in (message.email_from or '')) or po.partner_id == message.author_id:
                po.sudo().write({'seven_days_notice': 'green'})
        return message
