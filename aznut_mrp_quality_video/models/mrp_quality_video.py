from odoo import fields, models


class MrpQualityVide(models.Model):
    _name = "mrp.quality.video"
    _description = "MRP Quality Video"
    
    production_id = fields.Many2one(
        "mrp.production",
        string="Production Order",
    )
    video_link = fields.Char(
        string="Video Link",
    )
    is_manualy_recorded = fields.Boolean(
        string="Is Manualy Recorded"
    )
