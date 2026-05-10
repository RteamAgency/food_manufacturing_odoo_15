from odoo import models, api


class MailActivity(models.Model):
    _inherit = "mail.activity"
    
    
    @api.model_create_multi
    def create(self, vals_list):
        activities = super(MailActivity, self).create(vals_list)
        if not self.env.context.get('is_dashboard_action'):
            for activity in activities:
                email_from = (self.env.company.partner_id.email_formatted
                        or self.env.user.email_formatted
                        or self.env.ref('base.user_root').email_formatted)
                mail_values = {
                    'auto_delete': False,
                    'author_id': self.env.user.partner_id.id,
                    'email_from': email_from,
                    'email_to': activity.user_id.email_formatted,
                    'body_html': f'Mail activity {activity.summary or ""} assigned to you',
                    'subject': "New mail activity assigned to you",
                    'reply_to': '',
                }
                mail_id = self.env['mail.mail'].sudo().create(mail_values)
                mail_id.sudo().send()
        return activities
