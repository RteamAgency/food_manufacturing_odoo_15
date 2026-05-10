from odoo import fields, models, _
import requests
from datetime import timedelta
from odoo.http import request
from odoo.exceptions import UserError


GOOGLE_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'
ONEDRIVE_SCOPE = ['https://graph.microsoft.com/.default']
headers = {"content-type": "application/x-www-form-urlencoded"}

class ResCompany(models.Model):
    _inherit = "res.company"
    
    store_video_on = fields.Selection(
        selection=[
            ('gdrive', 'Google Drive'),
            ('onedrive', "OneDrive"),
        ],
        string="Store video on",
        default="onedrive",
        required=True,
    )
    
    # Settings for Google Drive Connect
    google_drive_video_client_secret = fields.Char(
        string="Google Drive Client Secret",
    )
    google_drive_video_client_id = fields.Char(
        string="Google Drive Client ID",
    )
    google_drive_video_redirect_url = fields.Char(
        string="Google Drive Redirect URL",
    )
    google_drive_video_access_token = fields.Char(
        string='Google Drive Access Token',
        help='The access token for the Google Drive account'
    )
    google_drive_video_refresh_token = fields.Char(
        string='Google Drive Refresh Token',
        help='The access token for the Google Drive account'
    )
    google_drive_video_token_validity = fields.Datetime(
        string='Google Drive Token Validity', copy=False,
        help='Specify the validity period of the Google Drive access token.'
    )
    google_drive_video_folder_id = fields.Char(
        string='Google Drive Video Folder',
    )
    
    # Settings for One Drive Connect
    onedrive_client_key = fields.Char(
        string='Onedrive Client ID'
    )
    onedrive_client_secret = fields.Char(
        string='Onedrive Client Secret',
    )
    onedrive_access_token = fields.Char(
        string='Onedrive Access Token',
    )
    onedrive_token_validity = fields.Datetime(
        string='Onedrive Token Validity',
    )
    onedrive_folder_key = fields.Char(
        string='Folder ID',
    )
    one_drive_video_sharepoint_url = fields.Char(
        string="OneDrive SharePoint Folder URL"
    )
    one_drive_video_drive_id = fields.Char(
        string="OneDrive Sharepoint ID",
    )
    one_drive_video_folder_id = fields.Char(
        string="OneDrive Folder ID",
    )
    onedrive_tenant_id = fields.Char(
        string="OneDrive Tenant ID"
    )

    def get_gdrive_tokens(self, authorize_code):
        """Generate onedrive tokens from authorization code"""
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        data = {
            'code': authorize_code,
            'client_id': self.google_drive_video_client_id,
            'client_secret': self.google_drive_video_client_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': base_url + '/google_drive/authentication'
        }
        try:
            res = requests.post(GOOGLE_TOKEN_ENDPOINT, params=data,headers=headers)
            res.raise_for_status()
            response = res.content and res.json() or {}
            if response:
                expires_in = response.get('expires_in')
                self.write({
                    'google_drive_video_access_token': response.get('access_token'),
                    'google_drive_video_refresh_token': response.get('refresh_token'),
                    'google_drive_video_token_validity': fields.Datetime.now() + timedelta(
                        seconds=expires_in) if expires_in else False,
                })
        except Exception:
            raise Exception('Authentification Error')
        
    def generate_gdrive_refresh_token(self):
        """Generate Google Drive access token from refresh token if expired"""
        data = {
            'refresh_token': self.google_drive_video_refresh_token,
            'client_id': self.google_drive_video_client_id,
            'client_secret': self.google_drive_video_client_secret,
            'grant_type': 'refresh_token',
        }
        try:
            res = requests.post(GOOGLE_TOKEN_ENDPOINT, data=data,
                                headers=headers)
            res.raise_for_status()
            response = res.content and res.json() or {}
            if response:
                expires_in = response.get('expires_in')
                self.write({
                    'google_drive_video_access_token': response.get('access_token'),
                    'google_drive_video_token_validity': fields.Datetime.now() + timedelta(
                        seconds=expires_in) if expires_in else False,
                })
        except requests.HTTPError as error:
            error_key = error.response.json().get("error", "nc")
            error_msg = _(
                "An error occurred while generating the token. Your "
                "authorization code may be invalid or has already expired [%s]."
                "You should check your Client ID and secret on the Google "
                "APIs plateform or try to stop and restart your calendar "
                "synchronisation.",
                error_key)
            raise UserError(error_msg)

    def action_get_onedrive_auth_code(self):
        """Generate onedrive tokens from authorization code"""
        token_url = f"https://login.microsoftonline.com/{self.onedrive_tenant_id}/oauth2/v2.0/token"
        data = {
            'client_id': self.onedrive_client_key,
            'client_secret': self.onedrive_client_secret,
            'grant_type': 'client_credentials',
            'scope': ONEDRIVE_SCOPE,
        }
        try:
            res = requests.post(token_url, data=data, headers=headers)
            res.raise_for_status()
            response = res.content and res.json() or {}
            if response:
                expires_in = response.get('expires_in')
                self.write({
                    'onedrive_access_token': response.get('access_token'),
                    'onedrive_token_validity': fields.Datetime.now() + timedelta
                    (seconds=expires_in) if expires_in else False,
                })
        except Exception as e:
            raise Exception('Authentification Error')
