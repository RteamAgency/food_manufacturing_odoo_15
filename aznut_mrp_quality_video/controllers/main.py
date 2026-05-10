import json
import requests
import datetime
from odoo import http, fields
from odoo.http import request
import urllib.parse
import re

MICROSOFT_GRAPH_END_POINT = "https://graph.microsoft.com"

def get_or_create_month_folder_gdrive(parent_folder_id, access_token):
    month_name = datetime.datetime.now().strftime('%B %Y')
    query = (
        f"name = '{month_name}' and mimeType = 'application/vnd.google-apps.folder' "
        f"and '{parent_folder_id}' in parents and trashed = false"
    )

    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'q': query, 'fields': 'files(id, name)'}

    response = requests.get(
        'https://www.googleapis.com/drive/v3/files',
        headers=headers,
        params=params
    )

    folder_list = response.json().get('files', [])
    if folder_list:
        return folder_list[0]['id']

    metadata = {
        'name': month_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id],
    }

    response = requests.post(
        'https://www.googleapis.com/drive/v3/files',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        },
        data=json.dumps(metadata),
    )

    folder = response.json()
    return folder['id']


class VideoRecorder(http.Controller):
    
    @http.route('/packaging/send_quality_video', type='http', auth='public', csrf=False)
    def upload_video(self, **kwargs):
        company_id = request.env.company
        storage = company_id.store_video_on
        
        if storage == 'gdrive':
            return self.google_drive_upload_video(**kwargs)
        elif storage == 'onedrive':
            return self.one_drive_upload_video(**kwargs)
        else:
            return "Invalid storage configuration", 400

    def google_drive_upload_video(self, **kwargs):
        company_id = request.env.company
        is_token_invalid = company_id.google_drive_video_token_validity <= fields.Datetime.now()
        if (company_id.google_drive_video_token_validity is not False and is_token_invalid):
            company_id.generate_gdrive_refresh_token()
        
        video_file = request.httprequest.files.get('video')
        if not video_file:
            return "No video file received", 400

        access_token = company_id.google_drive_video_access_token
        root_folder_id = company_id.google_drive_video_folder_id

        target_folder_id = get_or_create_month_folder_gdrive(root_folder_id, access_token)

        metadata = {
            'name': video_file.filename,
            'parents': [target_folder_id],
        }

        files = {
            'metadata': ('metadata', json.dumps(metadata), 'application/json'),
            'file': (video_file.filename, video_file.stream, video_file.content_type),
        }

        headers = {
            'Authorization': f'Bearer {access_token}',
        }

        response = requests.post(
            'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',
            headers=headers,
            files=files,
        )

        if response.status_code in (200, 201):
            file_info = response.json()
            file_id = file_info.get('id')
            if file_id:
                file_url = f"https://drive.google.com/file/d/{file_id}/view"
                request.env['mrp.quality.video'].sudo().create({
                    'production_id': int(kwargs.get('mo_id')),
                    'video_link': file_url,
                })
            else:
                return "Upload succeeded but no file ID returned", 500
        else:
            return f"Upload failed: {response.text}", 500
        
    def one_drive_upload_video(self, **kwargs):
        company_id = request.env.company
        is_token_invalid = company_id.onedrive_token_validity <= fields.Datetime.now()
        if (company_id.onedrive_token_validity is not False and is_token_invalid):
            company_id.action_get_onedrive_auth_code()

        video_file = request.httprequest.files.get('video')
        if not video_file:
            return "No video file received", 400

        access_token = company_id.onedrive_access_token
        headers = {
            'Authorization': 'Bearer %s' % access_token,
            'Content-Type': 'application/json'
        }
        sanitized_filename = re.sub(r'[\\/:"*?<>|]+', '_', video_file.filename)
        safe_filename = urllib.parse.quote(sanitized_filename, safe='')
        upload_session_url = (
            f"https://graph.microsoft.com/v1.0/sites/{company_id.one_drive_video_drive_id}/drive/items/{company_id.one_drive_video_folder_id}:/"
            f"{safe_filename}:/createUploadSession"
        )
        upload_session = requests.post(upload_session_url,headers=headers)
        upload_url = upload_session.json().get('uploadUrl')
        video_content = video_file.read()
        upload_headers = {
            'Content-Range': f'bytes 0-{len(video_content)-1}/{len(video_content)}',
            'Content-Length': str(len(video_content)),
            'Content-Type': video_file.content_type,
        }
        response = requests.put(upload_url, headers=upload_headers, data=video_content)
        if response.status_code in (200, 201):
            file_info = response.json()
            if file_info.get('webUrl'):
                request.env['mrp.quality.video'].sudo().create({
                    'production_id': int(kwargs.get('mo_id')),
                    'video_link': file_info.get('webUrl'),
                })
            else:
                return "Upload succeeded but no file URL returned", 500
        else:
            return f"Upload failed: {response.text}", 500
