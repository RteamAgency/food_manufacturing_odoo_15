from odoo import models
import datetime


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"
    
    def generate_batch_action(self, date_type):
        current_date = datetime.datetime.now()
        if date_type == 'yesterday':
            yesterday =  (current_date - datetime.timedelta(days=1)).date()
            start_date = datetime.datetime.combine(yesterday, datetime.time.min)
            end_date = datetime.datetime.combine(yesterday, datetime.time.max)
        
        if date_type == 'month':
            start_date = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = current_date

        work_orders = self.env['mrp.workorder'].search([
            ('date_finished', '>=', start_date),
            ('date_finished', '<=', end_date),
        ])
        production_work_orders = work_orders.filtered(lambda rec: rec.workcenter_id.production_station)
        exceeded_work_orders = production_work_orders.filtered(lambda rec: rec.workorder_batch_ids.filtered(lambda rec: rec.time_actual >= 15))
        return {'action': {
            'view_id': self.env.ref('mrp.mrp_production_workorder_tree_editable_view').id,
            'domain': [('id', 'in', exceeded_work_orders.ids)]
        }}
