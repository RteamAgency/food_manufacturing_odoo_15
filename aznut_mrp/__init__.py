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

from . import models
from . import wizards
from . import report

from collections import defaultdict
from odoo.tools.misc import OrderedSet


from odoo import SUPERUSER_ID, _, api, fields
from odoo.addons.stock.models.stock_rule import ProcurementException
from odoo.addons.mrp.models.stock_rule import StockRule
from odoo.addons.mrp.models.mrp_workorder import MrpWorkorder
from odoo.addons.mrp.models.stock_orderpoint import StockWarehouseOrderpoint
from odoo.addons.mrp.report.mrp_report_bom_structure import ReportBomStructure
from odoo.addons.mrp_workorder.models.mrp_workorder import MrpProductionWorkcenterLine
from odoo.addons.stock.models.stock_move import StockMove

from odoo.tools import float_compare, float_round, float_is_zero
from odoo.exceptions import UserError


def post_load_hook():
    @api.model
    def _run_manufacture(self, procurements):
        if self._context.get('not_create_mo'):
            return True
        productions_values_by_company = defaultdict(list)
        errors = []
        for procurement, rule in procurements:
            if float_compare(procurement.product_qty, 0, precision_rounding=procurement.product_uom.rounding) <= 0:
                continue
            bom = rule._get_matching_bom(procurement.product_id, procurement.company_id, procurement.values)

            productions_values_by_company[procurement.company_id.id].append(rule._prepare_mo_vals(*procurement, bom))

        if errors:
            raise ProcurementException(errors)

        for company_id, productions_values in productions_values_by_company.items():
            productions = self.env['mrp.production'].with_user(SUPERUSER_ID).sudo().with_company(company_id).create(
                productions_values)
            self.env['stock.move'].sudo().create(productions._get_moves_raw_values())
            self.env['stock.move'].sudo().create(productions._get_moves_finished_values())
            productions._create_workorder()
            if self._context.get('confirm_mo', True):
                productions.filtered(self._should_auto_confirm_procurement_mo).action_confirm()

            for production in productions:
                origin_production = production.move_dest_ids and production.move_dest_ids[
                    0].raw_material_production_id or False
                orderpoint = production.orderpoint_id
                if orderpoint and orderpoint.create_uid.id == SUPERUSER_ID and orderpoint.trigger == 'manual':
                    production.message_post(
                        body=_('This production order has been created from Replenishment Report.'),
                        message_type='comment',
                        subtype_xmlid='mail.mt_note')
                elif orderpoint:
                    production.message_post_with_view(
                        'mail.message_origin_link',
                        values={'self': production, 'origin': orderpoint},
                        subtype_id=self.env.ref('mail.mt_note').id)
                elif origin_production:
                    production.message_post_with_view(
                        'mail.message_origin_link',
                        values={'self': production, 'origin': origin_production},
                        subtype_id=self.env.ref('mail.mt_note').id)
        return True

    def _get_duration_expected(self, alternative_workcenter=False, ratio=1):
        self.ensure_one()
        if not self.workcenter_id:
            return self.duration_expected
        if self.workcenter_id.production_station or self.workcenter_id.premix_station or self.workcenter_id.packaging_station:
            if self.operation_id.time_cycle and self.production_id.batches_count:
                return self.operation_id.time_cycle * self.production_id.batches_count
        bathes_cutting_time = self.workcenter_id.cutting_time * self.production_id.batches_count
        if not self.operation_id:
            duration_expected_working = (
                                                self.duration_expected - self.workcenter_id.time_start - self.workcenter_id.time_stop) * self.workcenter_id.time_efficiency / 100.0
            if duration_expected_working < 0:
                duration_expected_working = 0
            return (
                    self.workcenter_id.time_start + self.workcenter_id.time_stop + duration_expected_working * ratio * 100.0 / self.workcenter_id.time_efficiency) + bathes_cutting_time
        qty_production = self.production_id.product_uom_id._compute_quantity(self.qty_production,
                                                                             self.production_id.product_id.uom_id)
        cycle_number = float_round(qty_production / self.workcenter_id.capacity, precision_digits=0,
                                   rounding_method='UP')
        if alternative_workcenter:
            alternative_cutting_time = alternative_workcenter.cutting_time * self.production_id.batches_count
            duration_expected_working = (
                                                self.duration_expected - self.workcenter_id.time_start - self.workcenter_id.time_stop) * self.workcenter_id.time_efficiency / (
                                                100.0 * cycle_number)
            if duration_expected_working < 0:
                duration_expected_working = 0
            alternative_wc_cycle_nb = float_round(qty_production / alternative_workcenter.capacity, precision_digits=0,
                                                  rounding_method='UP')
            return (
                    alternative_workcenter.time_start + alternative_workcenter.time_stop + alternative_wc_cycle_nb * duration_expected_working * 100.0 / alternative_workcenter.time_efficiency) + alternative_cutting_time
        time_cycle = self.operation_id.time_cycle
        return (
                self.workcenter_id.time_start + self.workcenter_id.time_stop + cycle_number * time_cycle * 100.0 / self.workcenter_id.time_efficiency) + bathes_cutting_time

    def _get_bom(self, bom_id=False, product_id=False, line_qty=False, line_id=False, level=False):
        bom = self.env['mrp.bom'].browse(bom_id)
        company = bom.company_id or self.env.company
        bom_quantity = line_qty
        if line_id:
            current_line = self.env['mrp.bom.line'].browse(int(line_id))
            bom_quantity = current_line.product_uom_id._compute_quantity(line_qty, bom.product_uom_id) or 0
        if product_id:
            product = self.env['product.product'].browse(int(product_id))
        else:
            product = bom.product_id or bom.product_tmpl_id.product_variant_id
        if product:
            attachments = self.env['mrp.document'].search(['|', '&', ('res_model', '=', 'product.product'),
                                                           ('res_id', '=', product.id), '&',
                                                           ('res_model', '=', 'product.template'),
                                                           ('res_id', '=', product.product_tmpl_id.id)])
        else:
            product = bom.product_tmpl_id
            attachments = self.env['mrp.document'].search(
                [('res_model', '=', 'product.template'), ('res_id', '=', product.id)])
        operations = self._get_operation_line(product, bom,
                                              float_round(bom_quantity, precision_rounding=1, rounding_method='UP'), 0)
        quantities_info = self._get_quantities_info(product, bom.product_uom_id)

        lines = {
            'bom': bom,
            'bom_qty': bom_quantity,
            'bom_prod_name': product.display_name,
            'currency': company.currency_id,
            'product': product,
            'code': bom and bom.display_name or '',
            'quantity_available': quantities_info.get('free_qty', 0),
            'quantity_on_hand': quantities_info.get('on_hand_qty', 0),
            'price': product.uom_id._compute_price(product.with_company(company).standard_price,
                                                   bom.product_uom_id) * bom_quantity,
            'total': sum([op['total'] for op in operations]),
            'level': level or 0,
            'operations': operations,
            'operations_cost': sum([op['total'] for op in operations]),
            'attachments': attachments,
            'operations_time': sum([op['duration_expected'] for op in operations])
        }
        components, total = self._get_bom_lines(bom, bom_quantity, product, line_id, level)
        warehouse = self.env['stock.warehouse'].browse(self.get_warehouses()[0]['id'])
        product_info = {}
        self._update_product_info(product, bom.id, product_info, warehouse, bom_quantity, bom=bom, parent_bom=False)

        if any([c['stock_avail_state'] == 'unavailable' for c in components]):
            lines.update({
                'availability_display': 'Not Available',
                'availability_state': 'unavailable',
            })
        elif any([c['stock_avail_state'] == 'expected' for c in components]):
            lines.update({
                'availability_display': 'Expected',
                'availability_state': 'unavailable',
            })
        elif all([c['stock_avail_state'] == 'available' for c in components]):
            lines.update({
                'availability_display': 'Available',
                'availability_state': 'available',
            })
        else:
            lines.update({
                'availability_display': 'Not Found',
                'availability_state': 'unavailable',
            })

        lines['components_available'] = all([c['stock_avail_state'] == 'available' for c in components])
        lines['total'] += total
        lines['components'] = components
        byproducts, byproduct_cost_portion = self._get_byproducts_lines(bom, bom_quantity, level, lines['total'])
        lines['byproducts'] = byproducts
        lines['cost_share'] = float_round(1 - byproduct_cost_portion, precision_rounding=0.0001)
        lines['bom_cost'] = lines['total'] * lines['cost_share']
        lines['byproducts_cost'] = sum(byproduct['bom_cost'] for byproduct in byproducts)
        lines['byproducts_total'] = sum(byproduct['product_qty'] for byproduct in byproducts)
        lines['extra_column_count'] = self._get_extra_column_count()
        return lines

    def _get_bom_lines(self, bom, bom_quantity, product, line_id, level):
        components = []
        total = 0
        for line in bom.bom_line_ids:
            line_quantity = (bom_quantity / (bom.product_qty or 1.0)) * line.product_qty
            product_info = {}
            warehouse = self.env['stock.warehouse'].browse(self.get_warehouses()[0]['id'])
            self._update_product_info(product, bom.id, product_info, warehouse, bom_quantity, bom=bom, parent_bom=False)
            quantities_info = self._get_quantities_info(line.product_id, line.product_uom_id)
            availabilities = self._get_availabilities(product, line_quantity, product_info, bom.id, quantities_info,

                                                      components)
            if line._skip_bom_line(product):
                continue
            company = bom.company_id or self.env.company
            price = line.product_id.uom_id._compute_price(line.product_id.with_company(company).standard_price,
                                                          line.product_uom_id) * line_quantity
            if line.child_bom_id:
                factor = line.product_uom_id._compute_quantity(line_quantity, line.child_bom_id.product_uom_id)
                sub_total = self._get_price(line.child_bom_id, factor, line.product_id)
                byproduct_cost_share = sum(line.child_bom_id.byproduct_ids.mapped('cost_share'))
                if byproduct_cost_share:
                    sub_total *= float_round(1 - byproduct_cost_share / 100, precision_rounding=0.0001)
            else:
                sub_total = price
            sub_total = self.env.company.currency_id.round(sub_total)

            components.append({
                'prod_id': line.product_id.id,
                'prod_name': line.product_id.display_name,
                'code': line.child_bom_id and line.child_bom_id.display_name or '',
                'quantity_available': quantities_info.get('free_qty', 0),
                'quantity_on_hand': quantities_info.get('on_hand_qty', 0),
                'prod_qty': line_quantity,
                'prod_uom': line.product_uom_id.name,
                'prod_cost': company.currency_id.round(price),
                'parent_id': bom.id,
                'line_id': line.id,
                'level': level or 0,
                'stock_avail_state': availabilities['stock_avail_state'],
                'availability_display': availabilities['availability_display'],
                'availability_state': availabilities['availability_state'],
                'total': sub_total,
                'child_bom': line.child_bom_id.id,
                'phantom_bom': line.child_bom_id and line.child_bom_id.type == 'phantom' or False,
                'attachments': self.env['mrp.document'].search(['|', '&',
                                                                ('res_model', '=', 'product.product'),
                                                                ('res_id', '=', line.product_id.id), '&',
                                                                ('res_model', '=', 'product.template'),
                                                                ('res_id', '=', line.product_id.product_tmpl_id.id)]),

            })
            total += sub_total
        return components, total

    def _post_process_scheduler(self):
        """ Confirm the productions only after all the orderpoints have run their
        procurement to avoid the new procurement created from the production conflict
        with them. """
        if self._context.get('confirm_mo', True):
            self.env['mrp.production'].sudo().search([
                ('orderpoint_id', 'in', self.ids),
                ('move_raw_ids', '!=', False),
                ('state', '=', 'draft'),
            ]).action_confirm()
        return super(StockWarehouseOrderpoint, self)._post_process_scheduler()

    def _next(self, continue_production=False):
        self.ensure_one()
        rounding = self.product_uom_id.rounding
        if float_compare(self.qty_producing, 0, precision_rounding=rounding) <= 0:
            raise UserError(_('Please ensure the quantity to produce is greater than 0.'))
        elif self.test_type in ('register_byproducts', 'register_consumed_materials'):
            if self.component_tracking != 'none' and not self.lot_id and self.qty_done != 0:
                raise UserError(_('Please enter a Lot/SN.'))
            if float_compare(self.qty_done, 0, precision_rounding=rounding) < 0:
                raise UserError(_('Please enter a positive quantity.'))

            self.component_remaining_qty -= float_round(self.qty_done,
                                                        precision_rounding=self.move_id.product_uom.rounding or rounding)
            if self.move_line_id:
                if self.move_line_id.product_id.tracking != 'none':
                    self.move_line_id = next((sml
                                              for sml in self.move_line_id.move_id.move_line_ids
                                              if sml.lot_id == self.lot_id and float_is_zero(sml.qty_done,
                                                                                             precision_rounding=sml.product_uom_id.rounding)),
                                             self.move_line_id)
                for move_line in self.move_id.move_line_ids:
                    move_line.write({
                        'qty_done': move_line.product_uom_qty,
                    })

            else:
                line = self.env['stock.move.line'].create(self._create_extra_move_lines())
                self.move_line_id = line[:1]
            if continue_production:
                self._create_subsequent_checks()

        if self.test_type == 'picture' and not self.picture:
            raise UserError(_('Please upload a picture.'))

        if not self.current_quality_check_id._is_pass_fail_applicable():
            self.current_quality_check_id.do_pass()

        self._change_quality_check(position='next', skipped=self.skip_completed_checks)
        if self.test_type in ('register_byproducts', 'register_consumed_materials'):
            self._update_component_quantity()

    def _action_done(self, cancel_backorder=False):
        moves = self.filtered(lambda move: move.state == 'draft')._action_confirm()
        moves = (self | moves).exists().filtered(lambda x: x.state not in ('done', 'cancel'))
        moves_ids_todo = OrderedSet()

        for move in moves:
            if move.quantity_done <= 0 and not move.is_inventory:
                if float_compare(move.product_uom_qty, 0.0, precision_rounding=move.product_uom.rounding) == 0 or cancel_backorder:
                    move._action_cancel()

        for move in moves:
            if move.state == 'cancel' or (move.quantity_done <= 0 and not move.is_inventory):
                continue

            moves_ids_todo |= move._create_extra_move().ids

        moves_todo = self.browse(moves_ids_todo)
        moves_todo._check_company()
        backorder_moves_vals = []
        for move in moves_todo:
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(move.quantity_done, move.product_uom_qty, precision_digits=rounding) < 0:
                qty_split = move.product_uom._compute_quantity(move.product_uom_qty - move.quantity_done, move.product_id.uom_id, rounding_method='HALF-UP')
                new_move_vals = move._split(qty_split)
                backorder_moves_vals += new_move_vals
        backorder_moves = self.env['stock.move'].create(backorder_moves_vals)
        backorder_moves.with_context(bypass_entire_pack=True)._action_confirm(merge=False)
        if cancel_backorder:
            backorder_moves.with_context(moves_todo=moves_todo)._action_cancel()
        moves_todo.mapped('move_line_ids').sorted()._action_done()
        for result_package in moves_todo\
                .mapped('move_line_ids.result_package_id')\
                .filtered(lambda p: p.quant_ids and len(p.quant_ids) > 1):
            if len(result_package.quant_ids.filtered(lambda q: not float_is_zero(abs(q.quantity) + abs(q.reserved_quantity), precision_rounding=q.product_uom_id.rounding)).mapped('location_id')) > 1:
                raise UserError(_('You cannot move the same package content more than once in the same transfer or split the same package into two location.'))
        if any(ml.package_id and ml.package_id == ml.result_package_id for ml in moves_todo.move_line_ids):
            self.env['stock.quant']._unlink_zero_quants()
        picking = moves_todo.mapped('picking_id')
        moves_todo.write({'state': 'done', 'date': fields.Datetime.now()})

        new_push_moves = moves_todo.filtered(lambda m: m.picking_id.immediate_transfer)._push_apply()
        if new_push_moves:
            new_push_moves._action_confirm()

        if self.env.context.get('is_scrap'):
            return moves_todo

        if picking and not cancel_backorder:
            backorder = picking._create_backorder()
            if any([m.state == 'assigned' for m in backorder.move_lines]):
               backorder._check_entire_pack()
        return moves_todo

    @api.model
    def _run_pull(self, procurements):
        for procurement, rule in procurements:
            warehouse_id = rule.warehouse_id
            if not warehouse_id:
                warehouse_id = rule.location_id.warehouse_id
            manu_rule = rule.route_id.rule_ids.filtered(
                lambda r: r.action == 'manufacture' and r.warehouse_id == warehouse_id)
            if warehouse_id.manufacture_steps != 'pbm_sam' or not manu_rule:
                continue
            if rule.picking_type_id == warehouse_id.sam_type_id or (
                    warehouse_id.sam_loc_id and warehouse_id.sam_loc_id.parent_path in rule.location_src_id.parent_path
            ):
                if float_compare(procurement.product_qty, 0, precision_rounding=procurement.product_uom.rounding) < 0:
                    procurement.values['group_id'] = procurement.values['group_id'].stock_move_ids.filtered(
                        lambda m: m.state not in ['done', 'cancel']).move_orig_ids.group_id[:1]
                    continue
                manu_type_id = manu_rule[0].picking_type_id
                if manu_type_id:
                    name = manu_type_id.sequence_id.next_by_id()
                else:
                    name = self.env['ir.sequence'].next_by_code('mrp.production') or _('New')
                group = procurement.values.get('group_id')

                picking = group.sale_id.picking_ids.filtered(
                    lambda pick: pick.picking_type_code == 'internal' and pick.state not in ['done', 'cancel'])
                if self._context.get('not_create_mo') and picking:
                    procurement.values['group_id'] = picking.group_id
                elif group:
                    procurement.values['group_id'] = group.copy({'name': name})
                else:
                    procurement.values['group_id'] = self.env["procurement.group"].create({'name': name})
        return super(StockRule, self)._run_pull(procurements)

    def _defaults_from_move(self, move):
        self.ensure_one()
        move_line_ids = move.move_line_ids
        qty_reserved = sum(move_line_ids.mapped('product_uom_qty'))
        need = qty_reserved - move.quantity_done if (qty_reserved - move.quantity_done) > 0 else 0
        vals = {'move_id': move.id, 'qty_done': need}
        if move_line_ids:
            vals.update({
                'move_line_id': move_line_ids[:1].id,
                'lot_id': move_line_ids[:1].lot_id.id,
            })
        return vals

    StockRule._run_manufacture = _run_manufacture
    StockRule._run_pull = _run_pull
    MrpWorkorder._get_duration_expected = _get_duration_expected
    MrpProductionWorkcenterLine._defaults_from_move = _defaults_from_move
    ReportBomStructure._get_bom = _get_bom
    ReportBomStructure._get_bom_lines = _get_bom_lines
    StockWarehouseOrderpoint._post_process_scheduler = _post_process_scheduler
    MrpProductionWorkcenterLine._next = _next
    StockMove._action_done = _action_done
