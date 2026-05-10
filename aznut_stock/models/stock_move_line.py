from odoo import models, fields


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    _order = 'expiration_date,result_package_id desc, location_id asc, location_dest_id asc, picking_id asc, id'

    reserved_from_stock = fields.Boolean(
        string='Reserved From Stock',
    )
