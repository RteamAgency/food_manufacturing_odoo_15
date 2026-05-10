import json
from odoo import http
from odoo.http import request


class GoogledriveAuth(http.Controller):
    """Controller for handling OneDrive and google authentication
    Methods:
        gdrive_oauth2callback: Callback route for Google Drive authentication
        """

    @http.route('/google_drive/authentication', type='http', auth="public")
    def gdrive_oauth2callback(self, **kw):
        """Callback route for Google Drive authentication"""
        state = json.loads(kw['state'])
        request.env.company.get_gdrive_tokens(kw.get('code'))
        return request.redirect(state.get('url_return'))
