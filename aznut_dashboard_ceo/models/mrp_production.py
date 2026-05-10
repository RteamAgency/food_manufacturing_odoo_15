from odoo import fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    
    def generate_shedule_mo_action(self):
        return {'action': {
            'view_id': self.env.ref('mrp.mrp_production_tree_view').id,
            'domain': [('id', 'in', self.ids)]
        }}
