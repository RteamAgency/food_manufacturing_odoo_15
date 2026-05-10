################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2019 SmartTek (<https://smartteksas.com/>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
################################################################################

from odoo import models, fields, _
from odoo.tools.misc import OrderedSet
from odoo.exceptions import UserError


class StockQuant(models.Model):
    _inherit = "stock.quant"

    sales_ids = fields.Many2many(
        'sale.order',
        string='Sale Orders',
        compute='_compute_sales_ids'
    )
    show_unreserve_button = fields.Boolean(
        string='Show Unreserved Orders',
        compute='_compute_show_unreserve_button'
    )
    sales_quantitites = fields.Char(
        string='Sales Quantitites',
        compute='_compute_sales_ids'
    )

    def _compute_sales_ids(self):
        for quant in self:
            domain = [
                ('location_dest_id', '!=', quant.location_id.id),
                ('location_id', '=', quant.location_id.id),
                ('product_id', '=', quant.product_id.id),
                ('package_id', '=', quant.package_id.id),
                ('owner_id', '=', quant.owner_id.id),
                ('lot_id', '=', quant.lot_id.id),
                ('state', 'in', ['waiting', 'assigned', 'confirmed', 'partially_available'])
            ]
            move_lines = self.env['stock.move.line'].search(domain)
            sale_lines = move_lines.mapped('move_id.sale_line_id')

            order_line_dict = {}
            for sale_line in sale_lines:
                order_line_dict[sale_line.order_id.id] = order_line_dict.get(sale_line.order_id.id,
                                                                             0) + sum((move_lines & sale_line.move_ids.move_line_ids).mapped('product_uom_qty'))

            quant.sales_ids = list(order_line_dict.keys())
            quant.sales_quantitites = ', '.join(map(str, order_line_dict.values()))

    def _compute_show_unreserve_button(self):
        self.show_unreserve_button = False
        for quant in self:
            if quant.sales_ids:
                quant.show_unreserve_button = True

    def action_unreserve(self):
        self.ensure_one()
        moves_to_unreserve = OrderedSet()
        suitable_moves = self.sales_ids.picking_ids.filtered(
            lambda picking: picking.state not in ['cancel', 'done']).move_lines.filtered(
            lambda move: self.lot_id.id in move.move_line_ids.mapped('lot_id.id') and
                         move.product_id.id == self.product_id.id
        )
        for move in suitable_moves:
            if move.state == 'cancel' or (move.state == 'done' and move.scrapped):
                continue
            elif move.state == 'done':
                raise UserError(_("You cannot unreserve a stock move that has been set to 'Done'."))
            moves_to_unreserve.add(move.id)
        moves_to_unreserve = self.env['stock.move'].browse(moves_to_unreserve)

        ml_to_update, ml_to_unlink = OrderedSet(), OrderedSet()
        moves_not_to_recompute = OrderedSet()
        for ml in moves_to_unreserve.move_line_ids.filtered(
                lambda line: line.lot_id.id == self.lot_id.id and
                             line.location_id.id == self.location_id.id and
                             line.location_dest_id.id != self.location_id.id and
                             line.product_id.id == self.product_id.id
        ):
            if ml.qty_done:
                ml_to_update.add(ml.id)
            else:
                ml_to_unlink.add(ml.id)
                moves_not_to_recompute.add(ml.move_id.id)
        ml_to_update, ml_to_unlink = self.env['stock.move.line'].browse(ml_to_update), self.env[
            'stock.move.line'].browse(ml_to_unlink)
        moves_not_to_recompute = self.env['stock.move'].browse(moves_not_to_recompute)

        ml_to_update.write({'product_uom_qty': 0})
        ml_to_update.write({'reserved_from_stock': False})
        ml_to_unlink.unlink()
        (moves_to_unreserve - moves_not_to_recompute)._recompute_state()

    def action_reserve(self):
        self.ensure_one()
        moves = self.env['stock.move'].search([
            ('product_id', '=', self.product_id.id),
            ('state', 'not in', ['assigned', 'draft', 'cancel', 'done'])
        ]).filtered(lambda move: move.sale_line_id.order_id)
        allowed_sale_orders_ids = moves.mapped('sale_line_id.order_id')
        return {
            'name': _('Select Sale Orders To Reserve'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'reserve.sale.order.wizard',
            'view_id': self.env.ref('aznut_sale.reserve_sale_order_wizard_form').id,
            'target': 'new',
            'context': {
                'default_quant_id': self.id,
                'default_allowed_sale_orders_ids': allowed_sale_orders_ids.ids,
            }
        }

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        if self._context.get('quant_id'):
            needed_quant = self.env['stock.quant'].browse(self._context.get('quant_id'))
            quants = super()._gather(product_id, location_id, lot_id, package_id, owner_id, strict)
            return needed_quant if needed_quant in quants else self.env['stock.quant']
        return super()._gather(product_id, location_id, lot_id, package_id, owner_id, strict)
