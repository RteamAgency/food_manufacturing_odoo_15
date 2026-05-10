from odoo import fields, models, api
from datetime import timedelta


def check_is_late(lead, days):
    now = fields.Datetime.now()
    deadline = lead.message_to_partner_id.create_date + timedelta(days=days)
    return now > deadline


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    message_to_partner_id = fields.Many2one(
        'mail.message',
        compute='_compute_message_to_partner_id',
        string='Mail To Partner',
    )
    awaiting_answer = fields.Boolean(
        string='Awaiting Answer',
        compute='_compute_awaiting_answer',
        store=False,
    )
    mail_status = fields.Selection(
        [
            ('no_email_sent', 'No Email Sent'),
            ('first_email_sent', 'First Email Sent'),
            ('second_email_sent', 'Second Email Sent')
        ],
        string='Mail Status',
        copy=False,
    )
    manager_note = fields.Text(
        string='Manager Note',
    )
    zoom_meetings_ids = fields.Text(
        string='Zoom Meetings IDs',
        copy=False,
    )
    fireflies_description = fields.Text(
        string='Fireflies',
        readonly=True,
        copy=False,
    )
    show_send_calendly_link_button = fields.Boolean(
        string='Show Send Calendly Link',
        compute='_compute_show_send_calendly_link_button',
    )

    def _compute_show_send_calendly_link_button(self):
        for lead in self:
            lead.show_send_calendly_link_button = bool(lead.user_id.calendly_link)

    def _compute_message_to_partner_id(self):
        self = self.sudo()

        for lead in self:
            all_messages = self.env['mail.message'].search([
                ('model', '=', 'crm.lead'),
                ('res_id', 'in', lead.ids),
            ])
            suitable_messages = self.env['mail.message']
            for message in all_messages:
                email_list = [email_to for email_to in message.mapped('mail_ids.email_to') if email_to]
                if lead.partner_id.id in (message.notified_partner_ids | message.partner_ids).ids or (
                        lead.partner_id.id in message.mapped('mail_ids.recipient_ids.id') or (
                        lead.email_from or 'No mail') in ', '.join(email_list)):
                    suitable_messages |= message

            lead.message_to_partner_id = suitable_messages.sorted('create_date', reverse=True)[:1]

    def _compute_awaiting_answer(self):
        self.awaiting_answer = False
        for lead in self:
            if lead.message_to_partner_id and lead.email_from:
                has_reply = self.env['mail.message'].search_count([
                    ('model', '=', lead._name),
                    ('res_id', '=', lead.id),
                    ('email_from', 'ilike', lead.email_from)
                ]) > 0
                lead.awaiting_answer = not has_reply

    @api.model
    def get_follow_up_data(self):
        leads = self.env['crm.lead'].search([
            ('mail_status', '=', 'second_email_sent')
        ]).filtered(lambda ld: ld.awaiting_answer)
        return self.env.ref('aznut_portal.follow_up_lead_tree').id, ['id', 'in', leads.ids]

    def action_send_calendly_link(self):
        self.ensure_one()
        body = """
        <p>
        I would love to set up a brief call or Zoom meeting to discuss your project and show how we can help you move forward smoothly and efficiently.
        </p> 
        <p>
        Please let me know a convenient time, or feel free to provide additional details about your needs. 
        <a href='%s'>Calendly</a>
        </p>
        """ % self.user_id.calendly_link
        res = self.env['mail.compose.message'].create({
            'model': 'crm.lead',
            'res_id': self.id,
            'composition_mode': 'comment',
            'body': body,
            'subject': 'Zoom Meeting',
            'partner_ids': self.partner_id.ids,
        })
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'res_id': res.id,
            'target': 'new',
            'context': {
                'mark_as_sent': True,
                'custom_layout': "mail.mail_notification_light",
                'force_email': True,
            },
        }

    @api.model
    def create(self, vals):
        vals.setdefault('mail_status', 'no_email_sent')
        return super(CrmLead, self).create(vals)

    def _cron_mail_awaiting(self):
        first_mail_template = self.env['mail.template'].search([('name', 'ilike', 'Touch base')], limit=1)
        second_mail_template = self.env['mail.template'].search([('name', 'ilike', 'No Respond')], limit=1)
        if not first_mail_template or not second_mail_template:
            return

        leads = self.search([
            ('mail_status', 'in', ['no_email_sent', 'first_email_sent', 'second_email_sent']),
        ]).filtered(lambda ld: ld.awaiting_answer)

        for lead in leads:
            lead_vals = {}
            if check_is_late(lead, days=3) and lead.mail_status in ['no_email_sent', 'first_email_sent']:
                if lead.mail_status == 'no_email_sent':
                    first_mail_template.with_user(lead.user_id).send_mail(lead.id, force_send=True,
                                                                          notif_layout='mail.mail_notification_light')
                    lead_vals.update({'mail_status': 'first_email_sent'})
                elif lead.mail_status == 'first_email_sent':
                    second_mail_template.with_user(lead.user_id).send_mail(lead.id, force_send=True,
                                                                           notif_layout='mail.mail_notification_light')
                    lead_vals.update({'mail_status': 'second_email_sent'})
                    self.env['mail.activity'].create({
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                        'user_id': lead.user_id.id,
                        'res_id': lead.id,
                        'res_model_id': self.env.ref('crm.model_crm_lead').id,
                        'note': 'Customer Not Responding',
                        'date_deadline': fields.Date.today() + timedelta(days=7),
                        'summary': 'No Response',
                    })
            elif check_is_late(lead, days=7) and lead.mail_status == 'second_email_sent':
                lead_vals.update({'mail_status': False})
                stage = self.env['crm.stage'].search([('name', 'ilike', 'No Respond')], limit=1)
                if stage:
                    lead_vals.update({'stage_id': stage.id})
            if lead_vals:
                lead.write(lead_vals)
