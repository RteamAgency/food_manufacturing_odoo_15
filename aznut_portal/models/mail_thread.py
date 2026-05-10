from odoo import models, tools


def get_email_body(msg):
    plain_text = None
    html_text = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            if "attachment" not in content_disposition:
                if content_type == "text/plain" and plain_text is None:
                    plain_text = part.get_content()
                elif content_type == "text/html" and html_text is None:
                    html_text = part.get_content()
    else:
        content_type = msg.get_content_type()
        if content_type == "text/plain":
            plain_text = msg.get_content()
        elif content_type == "text/html":
            html_text = msg.get_content()

    return plain_text or html_text


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _routing_create_bounce_email(self, email_from, body_html, message, **mail_values):
        bounce_to = tools.decode_message_header(message, 'Return-Path') or email_from
        lead = self.env['crm.lead'].sudo().search([('email_from', '=', bounce_to)], limit=1)
        if lead:
            body = get_email_body(message)
            self.env['mail.message'].sudo().create({
                'res_id': lead.id,
                'model': 'crm.lead',
                'author_id': lead.partner_id.id,
                'email_from': bounce_to,
                'body': body,
            })
            stage = self.env.ref('aznut_portal.stage_mails')
            lead.sudo().write({
                'stage_id': stage.id,
            })
            return
        return super(MailThread, self)._routing_create_bounce_email(email_from, body_html, message, **mail_values)
