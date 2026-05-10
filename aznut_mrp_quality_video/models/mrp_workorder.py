from odoo import models, fields, api
import re

class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"
    
    
    last_time_video_record = fields.Float(
        string="Last Time Video Record",
        default=0.0,
        copy=False,
    )
    can_record_video = fields.Boolean(
        string="Can Record Video",
        copy=False,
    )
    
    def create_quality_video_alert(self, snapshot_data_url):
        self.ensure_one()
        params = self.env['ir.config_parameter'].sudo()
        quality_team_id = params.get_param('aznut_mrp_quality_video.quality_video_alert_team')
        base64_data = re.sub('^data:image/.+;base64,', '', snapshot_data_url)
        alert = self.env['quality.alert'].create({
            "title": "Metal Detector Fail",
            "product_tmpl_id": self.production_id.product_tmpl_id.id,
            "product_id": self.production_id.product_id.id,
            "workcenter_id": self.workcenter_id.id,
            "workorder_id": self.id,
            "is_from_quality_video": True,
            "lot_id": self.lot_id.id,
            "team_id": int(quality_team_id) if quality_team_id else self.env['quality.alert.team'].search([], limit=1).id
        })
        attachment = self.env['ir.attachment'].create({
            'name': f'{self.production_id.display_name}-Packaging-Fail.jpg',
            'datas': base64_data,
            'res_model': 'mrp.workorder',
            'res_id': self.id,
            'type': 'binary',
            'mimetype': 'image/jpeg',
        })
        alert.message_post(
            body="Metal Detector Fail", 
            attachment_ids=attachment.ids, 
            partner_ids=alert.team_id.message_partner_ids.ids
        )

    def get_total_recording_count(self):
        total_videos = self.env['mrp.quality.video'].search([
            ('production_id', '=', self.production_id.id),
        ])
        total_alerts = self.env['quality.alert'].search([
            ('workorder_id', '=', self.id), 
            ('is_from_quality_video', "=", True),
        ])
        return len(total_videos) + len(total_alerts)

    @api.model
    def create(self, vals):
        if 'can_record_video' not in vals:
            vals['can_record_video'] = True
        return super(MrpWorkorder, self).create(vals)

    def get_quality_video_delay(self):
        params = self.env['ir.config_parameter'].sudo()
        video_delay = params.get_param('aznut_mrp_quality_video.quality_video_delay')
        return video_delay

    def get_quality_video_max_duration(self):
        params = self.env['ir.config_parameter'].sudo()
        video_duration = params.get_param('aznut_mrp_quality_video.quality_video_max_duration')
        return video_duration
