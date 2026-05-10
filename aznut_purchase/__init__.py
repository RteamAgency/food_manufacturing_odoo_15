from . import models
from . import report
from . import controllers
from . import wizard

from odoo import _, fields
from odoo.tools import float_compare
from odoo.exceptions import UserError
from odoo.addons.stock.models.stock_quant import StockQuant


def post_load_hook():
    def _apply_inventory(self):
        move_vals = []
        if not self.user_has_groups('stock.group_stock_manager,aznut_purchase.group_receiving_operator'):
            raise UserError(_('Only a stock manager can validate an inventory adjustment.'))
        for quant in self:
            if float_compare(quant.inventory_diff_quantity, 0, precision_rounding=quant.product_uom_id.rounding) > 0:
                move_vals.append(
                    quant._get_inventory_move_values(quant.inventory_diff_quantity,
                                                     quant.product_id.with_company(
                                                         quant.company_id).property_stock_inventory,
                                                     quant.location_id))
            else:
                move_vals.append(
                    quant._get_inventory_move_values(-quant.inventory_diff_quantity,
                                                     quant.location_id,
                                                     quant.product_id.with_company(
                                                         quant.company_id).property_stock_inventory,
                                                     out=True))
        moves = self.env['stock.move'].with_context(inventory_mode=False).create(move_vals)
        moves._action_done()
        self.location_id.sudo().write({'last_inventory_date': fields.Date.today()})
        date_by_location = {loc: loc._get_next_inventory_date() for loc in self.mapped('location_id')}
        for quant in self:
            quant.inventory_date = date_by_location[quant.location_id]
        self.write({'inventory_quantity': 0, 'user_id': False})
        self.write({'inventory_diff_quantity': 0})

    StockQuant._apply_inventory = _apply_inventory
