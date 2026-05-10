from odoo import fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"
    
    
    quality_video_count = fields.Integer(
        string='Metal Detector Video Count', 
        compute='_compute_quality_video_count')
    
    def _compute_quality_video_count(self):
        for rec in self:
            video_ids = self.env['mrp.quality.video'].search([('production_id', '=', self.id)])
            if video_ids:
                rec.quality_video_count = len(video_ids)
            else:
                rec.quality_video_count = 0

    def action_open_quality_video(self):
        self.ensure_one()
        video_ids = self.env['mrp.quality.video'].search([('production_id', '=', self.id)])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Metal Detector Report',
            'res_model': 'mrp.quality.video',
            'views': [[self.env.ref('aznut_mrp_quality_video.mrp_quality_video_tree_view').id, 'tree']],
            'domain': [('id', 'in', video_ids.ids)],
            'target': 'main',
        }
