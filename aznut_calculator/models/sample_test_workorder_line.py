from odoo import fields, models


class SampleTestWorkorderLine(models.Model):
    _name = 'sample.test.workorder.line'
    _description = 'Sample Test Workorder Line'

    product_id = fields.Many2one(
        related='move_id.product_id',
    )
    move_id = fields.Many2one(
        'stock.move',
        string='Move',
        required=True,
    )
    lots = fields.Char(
        string='Lots',
        compute='_compute_lots_quantities_locations_uoms',
    )
    quantities = fields.Char(
        string='Quantities',
        compute='_compute_lots_quantities_locations_uoms',
    )
    locations = fields.Char(
        string='Locations',
        compute='_compute_lots_quantities_locations_uoms',
    )
    uoms_ids = fields.Many2many(
        'uom.uom',
        string='UoMs',
        compute='_compute_lots_quantities_locations_uoms',
    )
    workorder_id = fields.Many2one(
        'mrp.workorder',
        string='Workorder',
        required=True,
    )

    def _compute_lots_quantities_locations_uoms(self):
        for line in self:
            move_lines = line.move_id.move_line_ids
            line.lots = ', '.join(move_lines.mapped('lot_id.name'))
            line.quantities = ', '.join(map(lambda qt: str(qt), move_lines.mapped('qty_done')))
            line.locations = ', '.join(move_lines.mapped('location_id.display_name'))
            line.uoms_ids = move_lines.mapped('product_uom_id')

    def action_change(self):
        self.ensure_one()
        return self.move_id.action_show_details()
