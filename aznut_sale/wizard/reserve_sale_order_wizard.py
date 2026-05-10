################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2023 SmartTek (<https://smartteksas.com>).
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

from odoo import models, fields
from odoo.exceptions import ValidationError


class ReserveSaleOrderWizard(models.TransientModel):
    _name = 'reserve.sale.order.wizard'
    _description = 'Reserve Sale Order Wizard'

    order_id = fields.Many2one(
        'sale.order',
        string='Sale Orders',
    )
    allowed_sale_orders_ids = fields.Many2many(
        'sale.order',
        'allowed_sale_orders',
        string='Allowed Sale Orders',
        store=True,
    )
    quant_id = fields.Many2one(
        'stock.quant',
        required=True,
        string='Quant',
    )
    quantity = fields.Float(
        string='Quantity',
    )

    def action_confirm(self):
        self.ensure_one()
        if not self.quantity:
            raise ValidationError("You need to provide quantity to reserve!")
        lines = self.order_id.order_line.filtered(lambda sol: sol.product_id == self.quant_id.product_id)
        quantity_to_reserve = self.quantity / len(lines)
        for line in lines:
            move = line.move_ids.filtered(lambda mv: mv.state in ['confirmed', 'waiting', 'partially_available'])[:1]
            total_reserved = sum(move.mapped('move_line_ids.product_uom_qty')) + quantity_to_reserve
            available_quantity = move._get_available_quantity(
                self.quant_id.location_id, lot_id=self.quant_id.lot_id, package_id=self.quant_id.package_id,
                owner_id=self.quant_id.owner_id, strict=True
            )

            if self.quantity > available_quantity:
                raise ValidationError(
                    'Not enough quantity on stock: %s - %s (Available)' % (self.quantity, available_quantity)
                )
            elif total_reserved > move.product_uom_qty:
                raise ValidationError(
                    'Total sum of new quantity is greater than consume quantity: %s > %s' % (
                        total_reserved, move.product_uom_qty)
                )

            move.with_context(quant_id=self.quant_id.id, missing_quantity=quantity_to_reserve)._action_assign()
            move._recompute_state()
        return {'type': 'ir.actions.act_window_close'}
