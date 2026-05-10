from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"
    
    def _action_send_mail(self, auto_commit=False):
        res = super(MailComposeMessage, self)._action_send_mail(auto_commit=auto_commit)
        if self.env.context.get('lead_message_copy', False):
            production_order = self.env['mrp.production'].browse(self.res_id)
            if production_order and production_order.sample_test_lead_id:
                message = self.env["mail.message"].search(
                    ["&", ("res_id", "=", self.res_id),("model", "=", self.model)],
                    order='create_date desc', limit=1)
                message.copy({
                    "model": "crm.lead", 
                    "res_id": production_order.sample_test_lead_id.id
                })
        return res
