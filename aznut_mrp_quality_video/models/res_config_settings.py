from odoo import fields, models
from odoo.http import request
from werkzeug import urls
import json


GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
ONEDRIVE_SCOPE = ['https://graph.microsoft.com/.default']
headers = {"content-type": "application/x-www-form-urlencoded"}

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    
    # Settings for Video Recording
    quality_video_delay = fields.Float(
        string="Quality Video Delay",
        config_parameter='aznut_mrp_quality_video.quality_video_delay',
        default="1.5",
    )
    quality_video_max_duration = fields.Float(
        string="Video Max Duration",
        config_parameter='aznut_mrp_quality_video.quality_video_max_duration',
        default="0.3333333333333333",
    )
    quality_video_alert_team = fields.Many2one(
        "quality.alert.team",
        string="Quality Alert Team",
        config_parameter='aznut_mrp_quality_video.quality_video_alert_team',
    )
    store_video_on = fields.Selection(
        related="company_id.store_video_on",
        readonly=False,
    )
    
    # Settings for Google Drive Connect
    google_drive_video_client_secret = fields.Char(
        related='company_id.google_drive_video_client_secret',
        readonly=False,
    )
    google_drive_video_client_id = fields.Char(
        related='company_id.google_drive_video_client_id',
        readonly=False,
    )
    google_drive_video_redirect_url = fields.Char(
        related='company_id.google_drive_video_redirect_url',
        readonly=False,
    )
    google_drive_video_access_token = fields.Char(
        related='company_id.google_drive_video_access_token',
        readonly=False,
    )
    google_drive_video_refresh_token = fields.Char(
        related='company_id.google_drive_video_refresh_token',
        readonly=False,
    )
    google_drive_video_token_validity = fields.Datetime(
        related='company_id.google_drive_video_token_validity',
        readonly=False,
    )
    google_drive_video_folder_id = fields.Char(
        related='company_id.google_drive_video_folder_id',
        readonly=False,
    )
    
    # Settings for One Drive Connect
    onedrive_client_key = fields.Char(
        related='company_id.onedrive_client_key',
        readonly=False,
    )
    onedrive_client_secret = fields.Char(
        related='company_id.onedrive_client_secret',
        readonly=False,
    )
    onedrive_access_token = fields.Char(
        related='company_id.onedrive_access_token',
        readonly=False,
    )
    onedrive_token_validity = fields.Datetime(
        related='company_id.onedrive_token_validity',
        readonly=False,
    )
    one_drive_video_sharepoint_url = fields.Char(
        related='company_id.one_drive_video_sharepoint_url',
        readonly=False,
    )
    one_drive_video_drive_id = fields.Char(
        related='company_id.one_drive_video_drive_id',
        readonly=False,
    )
    one_drive_video_folder_id = fields.Char(
        related='company_id.one_drive_video_folder_id',
        readonly=False,
    )
    onedrive_tenant_id = fields.Char(
        related='company_id.onedrive_tenant_id',
        readonly=False
    )


    def action_get_gdrive_auth_code(self):
        """Generate Google drive authorization code"""
        action = self.env["ir.actions.act_window"].sudo()._for_xml_id(
            "base_setup.action_general_configuration")
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        url_return = base_url + '/web#id=%d&action=%d&view_type=form&model=%s' % (
            4, action['id'], 'res.config.settings')
        state = {
            'url_return': url_return
        }
        encoded_params = urls.url_encode({
            'response_type': 'code',
            'client_id': self.google_drive_video_client_id,
            'scope': 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/drive.file',
            'redirect_uri': base_url + '/google_drive/authentication',
            'access_type': 'offline',
            'state': json.dumps(state),
            'approval_prompt': 'force',
        })
        auth_url = "%s?%s" % (GOOGLE_AUTH_ENDPOINT, encoded_params)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': auth_url,
        }

    def action_get_onedrive_auth_code(self):
        self.company_id.action_get_onedrive_auth_code()
