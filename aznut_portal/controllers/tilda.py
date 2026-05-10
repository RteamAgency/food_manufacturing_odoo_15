from odoo import http
from jinja2 import Markup

from odoo.http import request

from werkzeug.wrappers import Response
import traceback

MARKETING_FIELDS = {
    'utm_source': ('source_id', 'utm.source'),
    'utm_medium': ('medium_id', 'utm.medium'),
    'utm_campaign': ('campaign_id', 'utm.campaign'),
}


def replace_calendly(record, calendly_link, key):
    record[key] = record[key].replace('%calendly_link%', calendly_link)
    return record


def log_to_ir_logging(message, level='info', name='tilda.webhook', func='tilda_webhook'):
    request.env['ir.logging'].sudo().create({
        'name': name,
        'type': 'server',
        'dbname': request.env.cr.dbname,
        'level': level,
        'message': message,
        'path': name,
        'func': func,
        'line': 0,
    })


class TildaWebhookController(http.Controller):

    @http.route('/tilda/webhook', type='http', auth='public', csrf=False, methods=['POST'])
    def tilda_webhook(self, **post):
        try:
            name, email, phone = post.get('name'), post.get('email'), post.get('phone')
            url, comment, company_name = post.get('url'), post.get('comment'), post.get('company_name')

            if not name or not email:
                raise Exception('Missing name or email')

            user = request.env['res.users'].sudo().search([('name', '=', 'Jonathan')], limit=1) or request.env.user
            partner = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)

            if not partner:
                partner = request.env['res.partner'].with_user(user).sudo().create({
                    'name': email,
                    'email': email,
                    'phone': phone,
                })
            lead_vals = {
                'name': f'{name} opportunity',
                'website': url,
                'partner_name': company_name,
                'partner_id': partner.id,
                'description': comment,
                'contact_name': name,
                'user_id': user.id,
            }
            stage = request.env['crm.stage'].sudo().search([('name', 'ilike', 'New')], limit=1)
            if stage:
                lead_vals.update({
                    'stage_id': stage.id,
                })

            for utm_key, (lead_field, model_name) in MARKETING_FIELDS.items():
                utm_value = post.get(utm_key)
                if utm_value:
                    model = request.env[model_name].sudo()
                    record = model.search([('name', 'ilike', utm_value)], limit=1)
                    if not record:
                        record = model.create({'name': utm_value})
                    lead_vals[lead_field] = record.id

            lead = request.env['crm.lead'].with_user(user).sudo().create(lead_vals)
            calendly_link = Markup(
                '<a href="%s">Calendly</a>' % lead.user_id.calendly_link if lead.user_id.calendly_link else '')
            mail_template = request.env['mail.template'].sudo().search([
                ('name', 'ilike', 'Pet Supplements Inquire')
            ], limit=1)

            if mail_template and lead.user_id:
                email_values = mail_template.with_user(lead.user_id).generate_email(
                    lead.id, ['subject', 'body_html', 'email_from', 'email_to']
                )

                if '%calendly_link%' in email_values['body_html']:
                    email_values = replace_calendly(email_values, calendly_link, 'body_html')

                if email_values.get('body_html'):
                    try:
                        template = request.env.ref('mail.mail_notification_light', raise_if_not_found=True)
                    except ValueError:
                        pass
                    else:
                        record = request.env[mail_template.model].browse(lead.id)
                        model = request.env['ir.model']._get('crm.lead')

                        if mail_template.lang:
                            lang = mail_template._render_lang([lead.id])[lead.id]
                            template = template.with_context(lang=lang)
                            model = model.with_context(lang=lang)

                        message = request.env['mail.message'].sudo().new({
                            'body': email_values['body_html'],
                            'record_name': record.display_name,
                        })

                        template_ctx = {
                            'message': message,
                            'model_description': model.display_name,
                            'company': record.company_id if 'company_id' in record else request.env.company,
                            'record': record,
                        }

                        body = template._render(template_ctx, engine='ir.qweb', minimal_qcontext=True)
                        body = request.env['mail.render.mixin']._replace_local_links(body)

                        email_values['body_html'] = body

                email_values.update({
                    'email_to': False,
                    'recipient_ids': [(6, 0, partner.ids)],
                })

                mail = request.env['mail.mail'].with_user(lead.user_id.id).sudo().create(email_values)
                mail.with_user(lead.user_id.id).sudo().send()
                if '%calendly_link%' in mail.mail_message_id.body:
                    replace_calendly(mail.mail_message_id, calendly_link, 'body')

            log_to_ir_logging(f"Lead created with values: {lead_vals}")

            return Response('status=ok', content_type='application/x-www-form-urlencoded')

        except Exception as e:
            log_to_ir_logging(f"Webhook error: {str(e)}\n{traceback.format_exc()}", level='error')
            return Response('status=ok', content_type='application/x-www-form-urlencoded')
