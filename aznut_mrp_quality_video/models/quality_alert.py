from odoo import fields, models


class QualityAlert(models.Model):
    _inherit = "quality.alert"
    
    
    is_from_quality_video = fields.Boolean(
        string="Is From Quality Video",
    )

    def get_log_note_images(self):
        attachment_ids = self.message_ids.attachment_ids
        image_attachments = attachment_ids.filtered(lambda rec: rec.mimetype.startswith('image/'))
        return image_attachments
