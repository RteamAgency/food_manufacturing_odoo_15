from odoo import fields, models
from odoo.exceptions import ValidationError

from werkzeug.urls import url_join
import datetime
import base64
import requests

NEW_READABLE_FIELDS = [
    'calendly_link',
    'zoom_redirect_link',
    'zoom_client',
    'zoom_client_secret',
    'zoom_access_token',
    'zoom_access_token_expiry',
    'zoom_refresh_token',
    'zoom_authorization_code',
    'fireflies_token',
]
NEW_WRITABLE_FIELDS = [
    'calendly_link',
    'zoom_client',
    'zoom_client_secret',
    'fireflies_token',
]


class ResUsers(models.Model):
    _inherit = 'res.users'

    user_brands_ids = fields.Many2many(
        'product.attribute.value',
        string='Brands',
    )
    allowed_brands_ids = fields.Many2many(
        'product.attribute.value',
        'res_users_allowed_brands',
        compute='_compute_allowed_brands_ids',
        string='Allowed Brands',
    )
    calendly_link = fields.Char(
        string='Calendly Link',
        copy=False,
    )
    zoom_redirect_link = fields.Char(
        string='Zoom Redirect Link',
        compute='_compute_zoom_redirect_link',
        store=False,
    )
    zoom_client = fields.Char(
        string="Client Id",
        copy=False,
    )
    zoom_client_secret = fields.Char(
        string="Client Secret",
        copy=False,
    )
    zoom_access_token = fields.Char(
        string='Access Token',
        copy=False,
    )
    zoom_access_token_expiry = fields.Datetime(
        string='Access Token Expiry',
        copy=False,
        readonly=True,
    )
    zoom_refresh_token = fields.Char(
        string='Refresh Token',
        copy=False,
    )
    zoom_authorization_code = fields.Char(
        string="Authorization Code",
        copy=False,
    )
    fireflies_token = fields.Char(
        string="Fireflies Token",
    )

    def _compute_allowed_brands_ids(self):
        for user in self:
            attribute_values = self.env['product.attribute.value'].search([])
            allowed_brands_ids = attribute_values.filtered(lambda value: value.attribute_id.name.lower() == 'brand')
            user.allowed_brands_ids = allowed_brands_ids

    def _compute_zoom_redirect_link(self):
        for user in self:
            user.zoom_redirect_link = url_join(self.get_base_url(), 'zoom_authentication')

    def _check_zoom_credentials(self):
        self.ensure_one()
        if not self.zoom_client:
            raise ValidationError("Please Enter Client ID")
        if not self.zoom_client_secret:
            raise ValidationError("Please Enter Client Secret")
        if not self.zoom_redirect_link:
            raise ValidationError("Please Enter Redirect Link")

    def action_zoom_authenticate(self):
        self = self.sudo()
        self.ensure_one()
        self._check_zoom_credentials()
        client_id = self.zoom_client
        redirect_url = '%s/%s' % (self.zoom_redirect_link, self.id)
        auth_url = "https://zoom.us/oauth/authorize?response_type=code&client_id=%s&redirect_uri=%s"
        url = auth_url % (client_id, redirect_url)

        return {
            "type": 'ir.actions.act_url',
            "url": url,
            "target": "current"
        }

    def action_zoom_refresh_token(self):
        self = self.sudo()
        self.ensure_one()
        self._check_zoom_credentials()
        if not self.zoom_refresh_token:
            raise ValidationError('Refresh Token is not yet configured.')

        client_id = self.zoom_client
        client_secret = self.zoom_client_secret
        refresh_token = self.zoom_refresh_token

        data = {
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        }

        b64 = str(client_id + ":" + client_secret).encode('utf-8')
        b64 = base64.b64encode(b64).decode('utf-8')

        response = requests.post(
            'https://zoom.us/oauth/token', data=data,
            headers={
                'Authorization': 'Basic ' + b64,
                'content-type': 'application/x-www-form-urlencoded'},
            timeout=20)
        res = response.json()
        if res and res.get('access_token'):
            expires_in = res.get('expires_in')
            expiry = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
            self.write({
                'zoom_access_token': response.json().get('access_token'),
                'zoom_access_token_expiry': expiry,
            })
        else:
            raise ValidationError(
                'Something went wrong during the token generation.Please request again an authorization code.')

    def _cron_zoom_synchronization(self):
        users = self.env['res.users'].search([('zoom_refresh_token', '!=', False)])
        for user in users:
            try:
                user.action_zoom_refresh_token()
                headers = {
                    'Authorization': f'Bearer {user.zoom_access_token}',
                    'Content-Type': 'application/json'
                }
                url = 'https://api.zoom.us/v2/users/me/meetings?type=upcoming'
                response = requests.get(url, headers=headers)
                meetings = response.json()
                for meeting in meetings.get('meetings'):
                    join_url = meeting.get('join_url')
                    meeting_id = meeting.get('id')
                    if meeting_id and join_url:
                        meeting_url = f'https://api.zoom.us/v2/meetings/{meeting_id}'
                        meeting_response = requests.get(meeting_url, headers=headers)
                        meeting = meeting_response.json()
                        if meeting:
                            participants = meeting.get('settings').get('meeting_invitees')
                            participants_emails = [p.get('email') for p in participants if
                                                   p.get('email') and p.get('email') != meeting.get('host_email')]
                            lead = self.env['crm.lead'].search([
                                ('email_from', 'in', participants_emails),
                                ('zoom_meetings_ids', 'not ilike', meeting_id)
                            ], limit=1)
                            if lead:
                                lead.message_post(body='Client Initiated Zoom Meeting: %s' % join_url)
                                lead.write({'zoom_meetings_ids': '%s %s' % (lead.zoom_meetings_ids, meeting_id)})
            except (ValidationError, requests.exceptions.RequestException):
                continue

    def _cron_fireflies_synchronization(self):
        leads = self.env['crm.lead'].search([('zoom_meetings_ids', '!=', False)])
        users_with_fireflies = self.env['res.users'].search([('fireflies_token', '!=', False)])

        for lead in leads:
            notes = []
            for user in users_with_fireflies:
                token = user.fireflies_token
                if not token:
                    continue

                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }

                query = """
                query Transcripts($participantEmail: String) {
                  transcripts(participant_email: $participantEmail) {
                    id
                    date
                    title
                    summary {
                      action_items
                      shorthand_bullet
                    }
                  }
                }
                """

                variables = {
                    "participantEmail": lead.email_from
                }

                try:
                    response = requests.post(
                        "https://api.fireflies.ai/graphql",
                        headers=headers,
                        json={"query": query, "variables": variables},
                        timeout=10
                    )
                    response.raise_for_status()
                    data = response.json()
                except (requests.RequestException, ValueError):
                    continue

                if 'errors' in data:
                    continue

                transcripts = data.get("data", {}).get("transcripts", [])
                for transcript in transcripts:
                    try:
                        ms_date = transcript.get('date')
                        title = transcript.get('title')
                        if ms_date:
                            try:
                                date = datetime.datetime.utcfromtimestamp(ms_date / 1000)
                            except Exception:
                                date = 'Invalid date'
                        else:
                            date = 'No date'
                        if not title:
                            title = 'No title'
                        total_string = '%s - %s' % (title, date)
                        summary = transcript.get("summary", {})
                        action_items = summary.get("action_items", '')
                        shorthand_bullet = summary.get("shorthand_bullet", '')
                        total_string += '\nAction Items: %s' % action_items
                        total_string += '\nNotes: \n%s' % shorthand_bullet
                        notes.append(total_string)
                    except Exception:
                        pass

            lead.write({'fireflies_description': '\n'.join(notes) if notes else False})

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + NEW_READABLE_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + NEW_WRITABLE_FIELDS
