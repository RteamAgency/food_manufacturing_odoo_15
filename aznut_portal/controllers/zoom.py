import base64
import datetime
import requests
from odoo import http
from odoo.http import request
from odoo.exceptions import UserError


class ZoomMeetAuth(http.Controller):

    @http.route('/zoom_authentication/<int:user_id>', type="http", auth="public", website=True)
    def get_auth_code(self, code=None, user_id=None):
        if not user_id or not code:
            raise UserError('Missing required parameters: user_id or code.')

        user = request.env['res.users'].sudo().browse(user_id)
        if not user.exists():
            raise UserError('User not found.')

        user.write({'zoom_authorization_code': code})

        client_id = user.zoom_client
        client_secret = user.zoom_client_secret
        redirect_link = user.zoom_redirect_link

        auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

        data = {
            'code': code,
            'redirect_uri': '%s/%s' % (redirect_link, user.id),
            'grant_type': 'authorization_code'
        }

        try:
            response = requests.post(
                'https://zoom.us/oauth/token',
                data=data,
                headers={
                    'Authorization': f'Basic {auth_header}',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise UserError(f'Error communicating with Zoom: {e}')

        token_data = response.json()
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in')

        if access_token:
            expiry = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
            user.write({
                'zoom_access_token': access_token,
                'zoom_access_token_expiry': expiry,
                'zoom_refresh_token': refresh_token,
            })
            return "Authentication successful. You can close this window."
        else:
            raise UserError('Failed to retrieve access token from Zoom. Please verify your credentials.')
