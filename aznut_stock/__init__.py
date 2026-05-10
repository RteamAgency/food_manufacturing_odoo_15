from . import models
from odoo.addons.stock.models.stock_move import StockMove

from odoo.tools.misc import OrderedSet
from odoo.tools import float_is_zero, float_compare, float_round
from odoo.exceptions import UserError


def reserve_without_child_moves(move, missing_reserved_uom_quantity, assigned_moves_ids, partially_available_moves_ids):
    need = move.product_uom._compute_quantity(
        missing_reserved_uom_quantity,
        move.product_id.uom_id,
        rounding_method='HALF-UP'
    )
    rounding = move.product_id.uom_id.rounding
    if float_is_zero(need, precision_rounding=rounding):
        assigned_moves_ids.add(move.id)
        if move.id in partially_available_moves_ids:
            partially_available_moves_ids.remove(move.id)
        return assigned_moves_ids, partially_available_moves_ids

    forced_package_id = move.package_level_id.package_id or None
    available_quantity = move._get_available_quantity(
        move.location_id,
        package_id=forced_package_id
    )
    if available_quantity <= 0:
        return assigned_moves_ids, partially_available_moves_ids
    taken_quantity = move.with_context(reserved_from_stock=True)._update_reserved_quantity(
        need,
        available_quantity,
        move.location_id,
        package_id=forced_package_id,
        strict=False,
    )
    if float_is_zero(taken_quantity, precision_rounding=rounding):
        return assigned_moves_ids, partially_available_moves_ids
    if float_compare(need, taken_quantity, precision_rounding=rounding) == 0:
        assigned_moves_ids.add(move.id)
        if move.id in partially_available_moves_ids:
            partially_available_moves_ids.remove(move.id)
    else:
        if move.id not in partially_available_moves_ids:
            partially_available_moves_ids.add(move.id)
    return assigned_moves_ids, partially_available_moves_ids


def post_load_hook():
    def _action_assign(self):
        StockMove = self.env['stock.move']
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        reserved_availability = {move: move.reserved_availability for move in self}
        roundings = {move: move.product_id.uom_id.rounding for move in self}
        move_line_vals_list = []
        moves_to_redirect = OrderedSet()
        for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']):
            rounding = roundings[move]
            missing_reserved_uom_quantity = move.product_uom_qty - reserved_availability[move]
            force_missing_quantity = self.env.context.get('missing_quantity')
            if force_missing_quantity:
                missing_reserved_uom_quantity = force_missing_quantity
            missing_reserved_quantity = move.product_uom._compute_quantity(
                missing_reserved_uom_quantity,
                move.product_id.uom_id,
                rounding_method='HALF-UP'
            )
            if move._should_bypass_reservation():
                if move.move_orig_ids:
                    available_move_lines = move._get_available_move_lines(
                        assigned_moves_ids,
                        partially_available_moves_ids,
                    )
                    for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
                        qty_added = min(missing_reserved_quantity, quantity)
                        move_line_vals = move._prepare_move_line_vals(qty_added)
                        move_line_vals.update({
                            'location_id': location_id.id,
                            'lot_id': lot_id.id,
                            'lot_name': lot_id.name,
                            'owner_id': owner_id.id,
                            'package_id': package_id.id,
                        })
                        move_line_vals_list.append(move_line_vals)
                        missing_reserved_quantity -= qty_added
                        if float_is_zero(missing_reserved_quantity, precision_rounding=move.product_id.uom_id.rounding):
                            break

                if missing_reserved_quantity and move.product_id.tracking == 'serial' and (
                        move.picking_type_id.use_create_lots or move.picking_type_id.use_existing_lots):
                    for i in range(0, int(missing_reserved_quantity)):
                        move_line_vals_list.append(move._prepare_move_line_vals(quantity=1))
                elif missing_reserved_quantity:
                    to_update = move.move_line_ids.filtered(lambda ml: ml.product_uom_id == move.product_uom and
                                                                       ml.location_id == move.location_id and
                                                                       ml.location_dest_id == move.location_dest_id and
                                                                       ml.picking_id == move.picking_id and
                                                                       not ml.lot_id and
                                                                       not ml.package_id and
                                                                       not ml.owner_id)
                    if to_update:
                        to_update[0].product_uom_qty += move.product_id.uom_id._compute_quantity(
                            missing_reserved_quantity, move.product_uom, rounding_method='HALF-UP')
                    else:
                        move_line_vals_list.append(move._prepare_move_line_vals(quantity=missing_reserved_quantity))
                assigned_moves_ids.add(move.id)
                moves_to_redirect.add(move.id)
            else:
                if float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding):
                    assigned_moves_ids.add(move.id)
                elif not move.move_orig_ids:
                    if move.procure_method == 'make_to_order':
                        continue
                    assigned_moves_ids, partially_available_moves_ids = reserve_without_child_moves(
                        move,
                        missing_reserved_uom_quantity,
                        assigned_moves_ids,
                        partially_available_moves_ids,
                    )
                else:
                    qty_to_reserve = missing_reserved_uom_quantity
                    available_move_lines = move._get_available_move_lines(
                        assigned_moves_ids,
                        partially_available_moves_ids
                    )
                    if available_move_lines:
                        for move_line in move.move_line_ids.filtered(lambda m: m.product_qty):
                            if available_move_lines.get((move_line.location_id, move_line.lot_id, move_line.package_id,
                                                         move_line.owner_id)):
                                available_move_lines[(move_line.location_id, move_line.lot_id, move_line.package_id,
                                                      move_line.owner_id)] -= move_line.product_qty
                        for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
                            need = move.product_qty - sum(move.move_line_ids.mapped('product_qty'))
                            if force_missing_quantity:
                                need = missing_reserved_quantity
                            available_quantity = move._get_available_quantity(location_id, lot_id=lot_id,
                                                                              package_id=package_id, owner_id=owner_id,
                                                                              strict=True)
                            if float_is_zero(available_quantity, precision_rounding=rounding):
                                continue
                            taken_quantity = move._update_reserved_quantity(need, min(quantity, available_quantity),
                                                                            location_id, lot_id, package_id, owner_id)
                            if force_missing_quantity and taken_quantity:
                                to_reserve = missing_reserved_quantity - taken_quantity
                                if to_reserve > 0:
                                    missing_reserved_quantity = missing_reserved_uom_quantity = to_reserve
                                else:
                                    missing_reserved_quantity = missing_reserved_uom_quantity = 0

                            if float_is_zero(taken_quantity, precision_rounding=rounding):
                                continue
                            qty_to_reserve -= taken_quantity
                            moves_to_redirect.add(move.id)
                            if float_is_zero(need - taken_quantity, precision_rounding=rounding):
                                assigned_moves_ids.add(move.id)
                                break
                            partially_available_moves_ids.add(move.id)
                    if qty_to_reserve >0:
                        assigned_moves_ids, partially_available_moves_ids = reserve_without_child_moves(
                            move,
                            qty_to_reserve,
                            assigned_moves_ids,
                            partially_available_moves_ids,
                        )

            if move.product_id.tracking == 'serial':
                move.next_serial_count = move.product_uom_qty
        self.env['stock.move.line'].create(move_line_vals_list)
        StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
        StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})
        if not self.env.context.get('bypass_entire_pack'):
            self.picking_id._check_entire_pack()
        StockMove.browse(moves_to_redirect).move_line_ids._apply_putaway_strategy()

    def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None,
                                  owner_id=None, strict=True):

        self.ensure_one()
        reserved_from_stock = self._context.get('reserved_from_stock')

        if not lot_id:
            lot_id = self.env['stock.production.lot']
        if not package_id:
            package_id = self.env['stock.quant.package']
        if not owner_id:
            owner_id = self.env['res.partner']

        if self.product_packaging_id and self.product_id.product_tmpl_id.categ_id.packaging_reserve_method == "full":
            available_quantity = self.product_packaging_id._check_qty(available_quantity, self.product_id.uom_id,
                                                                      "DOWN")

        taken_quantity = min(available_quantity, need)
        if not strict and self.product_id.uom_id != self.product_uom:
            taken_quantity_move_uom = self.product_id.uom_id._compute_quantity(taken_quantity, self.product_uom,
                                                                               rounding_method='DOWN')
            taken_quantity = self.product_uom._compute_quantity(taken_quantity_move_uom, self.product_id.uom_id,
                                                                rounding_method='HALF-UP')

        quants = []
        rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        if self.product_id.tracking == 'serial':
            if float_compare(taken_quantity, int(taken_quantity), precision_digits=rounding) != 0:
                taken_quantity = 0

        self.env['base'].flush()
        try:
            with self.env.cr.savepoint():
                if not float_is_zero(taken_quantity, precision_rounding=self.product_id.uom_id.rounding):
                    quants = self.env['stock.quant']._update_reserved_quantity(
                        self.product_id, location_id, taken_quantity, lot_id=lot_id,
                        package_id=package_id, owner_id=owner_id, strict=strict
                    )
        except UserError:
            taken_quantity = 0

        serial_move_line_vals = []
        for reserved_quant, quantity in quants:
            to_update = next(
                (line for line in self.move_line_ids if line._reservation_is_updatable(quantity, reserved_quant)),
                False)
            if to_update:
                uom_quantity = self.product_id.uom_id._compute_quantity(quantity, to_update.product_uom_id,
                                                                        rounding_method='HALF-UP')
                uom_quantity = float_round(uom_quantity, precision_digits=rounding)
                uom_quantity_back_to_product_uom = to_update.product_uom_id._compute_quantity(uom_quantity,
                                                                                              self.product_id.uom_id,
                                                                                              rounding_method='HALF-UP')
            if to_update and float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
                to_update.with_context(bypass_reservation_update=True).product_uom_qty += uom_quantity
                if reserved_from_stock:
                    to_update.reserved_from_stock = True
            else:
                if self.product_id.tracking == 'serial':
                    vals_list = []
                    for move_line_val in range(int(quantity)):
                        vals = self._prepare_move_line_vals(quantity=1, reserved_quant=reserved_quant)
                        if reserved_from_stock:
                            vals.update({'reserved_from_stock': True})
                        vals_list.append(vals)
                    serial_move_line_vals.extend(vals_list)
                else:
                    vals = self._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
                    if reserved_from_stock:
                        vals.update({'reserved_from_stock': True})
                    self.env['stock.move.line'].create(vals)
        self.env['stock.move.line'].create(serial_move_line_vals)
        return taken_quantity

    StockMove._action_assign = _action_assign
    StockMove._update_reserved_quantity = _update_reserved_quantity
