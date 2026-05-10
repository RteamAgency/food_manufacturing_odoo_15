from odoo import fields, models


class MrpWorkorderBatch(models.Model):
    _inherit = "mrp.workorder.batch"
    
    production_id = fields.Many2one(
        related="workorder_id.production_id",
    )
    
    def generate_batch_action(self):
        return {'action': {
            'view_id': self.env.ref('aznut_dashboard_ceo.mrp_workorder_batch_view_tree').id,
            'domain': [('id', 'in', self.ids)],
        }}
