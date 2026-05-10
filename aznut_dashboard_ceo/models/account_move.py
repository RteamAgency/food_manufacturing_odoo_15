from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"
    
    def generate_open_invoice_action(self):
        return {'action': {
            'view_id': self.env.ref('account.view_out_invoice_tree').id,
            'domain': [('id', 'in', self.ids)]
        }}
