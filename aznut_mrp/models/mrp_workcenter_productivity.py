from odoo import fields, models, api


class MrpWorkcenterProductivity(models.Model):
    _inherit = "mrp.workcenter.productivity"

    mrp_workorder_batch_id = fields.Many2one(
        'mrp.workorder.batch',
        string='MRP Workorder Batch',
        compute='_compute_mrp_workorder_batch_id'
    )
    block_workorder_id = fields.Many2one(
        'mrp.workorder',
        string='Block Workorder',
    )

    @api.depends('date_start', 'workorder_id')
    def _compute_mrp_workorder_batch_id(self):
        for log in self:
            domain = [
                ('time_start', '<=', log.date_start),
                ('time_finish', '>=', log.date_start),
                ('is_validated', '=', True),
                ('workorder_id', '=', log.block_workorder_id.id)
            ]
            batch = self.env['mrp.workorder.batch'].search(domain, limit=1)
            log.mrp_workorder_batch_id = batch
