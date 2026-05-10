from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"
    
    def action_average_lead_time(self):
        self.ensure_one()
        return {
            'name': 'Vendor Lead Time Report',
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.lead.time.report',
            'view_mode': 'list',
            'views': [
                (self.env.ref('aznut_purchase.view_vendor_lead_time_report_tree').id, 'list')
            ],
            'context': {'report_partner_id': self.id, 'group_by': 'product_id'},
            'target': 'current',
        }
