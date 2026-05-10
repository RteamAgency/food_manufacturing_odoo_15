from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    
    def generate_waiting_answers_action(self):
        return {'action': {
            'view_id': self.env.ref('crm.crm_case_kanban_view_leads').id,
            'domain': [('id', 'in', self.ids)]
        }}
