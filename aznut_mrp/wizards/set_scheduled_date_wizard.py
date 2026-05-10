from odoo import models, fields


class SetScheduledDateWizard(models.TransientModel):
    _name = 'set.scheduled.date.wizard'
    _description = 'Set Scheduled Date Wizard'

    production_orders_ids = fields.Many2many(
        'mrp.production',
        string='Production Orders',
    )
    scheduled_date = fields.Datetime(
        string='Scheduled Date',
    )

    def action_confirm(self):
        self.ensure_one()
        for order in self.production_orders_ids:
            order.write({'date_planned_start': self.scheduled_date})
            order._onchange_date_planned_start()
