# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

categories_to_exclude = ['Dog Treats Packaging materials',
                         'Jar Labels']

block_states = ['waiting', 'confirmed', 'partially_available']


def update_checks(checks, qty, batches_count, component):
    qty_to_write = qty / (batches_count or 1)
    needed_check_lines = checks.filtered(lambda check: check.component_id == component)
    needed_check_lines.write({'quantity': qty_to_write})


class StockMove(models.Model):
    _inherit = 'stock.move'

    onhand_deficit = fields.Boolean(
        string="Onhand Deficit",
        compute="_compute_onhand_deficit",
    )
    can_edit = fields.Boolean(
        string="Can Edit",
        compute='_compute_can_edit',
    )

    def _compute_can_edit(self):
        self.can_edit = True
        for move in self:
            if (move.raw_material_production_id.state != 'done' and move.state == 'done') or not self.env.user.user_has_groups('mrp.group_mrp_manager,base.group_erp_manager'):
                move.can_edit = False

    @api.depends('product_id', 'product_uom_qty')
    def _compute_onhand_deficit(self):
        for rec in self:
            if rec.state in block_states:
                rec.onhand_deficit = rec.product_id.free_qty < rec.product_uom_qty
            else:
                rec.onhand_deficit = False

    def check_category(self):
        return self.product_id.categ_id.name not in categories_to_exclude

    def _get_relevant_state_among_moves(self):
        sort_map = {
            'assigned': 4,
            'waiting': 3,
            'partially_available': 2,
            'confirmed': 1,
        }
        moves_todo = self.filtered(lambda move:
                                   move.state not in ['cancel', 'done']
                                   and not (move.state == 'assigned' and not move.product_uom_qty))
        if self._context.get('from_mrp'):
            moves_todo = moves_todo.filtered(lambda move:
                                             not move.product_id.categ_id.is_removed_from_premix_availability)
        moves_todo = moves_todo.sorted(key=lambda move: (sort_map.get(move.state, 0), move.product_uom_qty))
        if not moves_todo:
            return 'assigned'
        if moves_todo[:1].picking_id and moves_todo[:1].picking_id.move_type == 'one':
            most_important_move = moves_todo[0]
            if most_important_move.state == 'confirmed':
                return 'confirmed' if most_important_move.product_uom_qty else 'assigned'
            elif most_important_move.state == 'partially_available':
                return 'confirmed'
            else:
                return moves_todo[:1].state or 'draft'
        elif moves_todo[:1].state != 'assigned' and any(
                move.state in ['assigned', 'partially_available'] for move in moves_todo):
            return 'partially_available'
        else:
            least_important_move = moves_todo[-1:]
            if least_important_move.state == 'confirmed' and least_important_move.product_uom_qty == 0:
                return 'assigned'
            else:
                return moves_todo[-1:].state or 'draft'

    def _update_manufacturing_checks(self):
        for move in self:
            mrp_order = self.env['mrp.production'].search([('move_raw_ids', 'in', move.ids)])[:1]
            if mrp_order:
                premix_wo = mrp_order.workorder_ids.filtered(lambda wo: wo.premix_station)
                premix_check_lines = premix_wo.check_ids.quality_check_premix_line_ids
                update_checks(premix_check_lines, move.product_uom_qty, mrp_order.batches_count, move.product_id)
                move._action_assign()
                production_wo = mrp_order.workorder_ids.filtered(lambda wo: wo.production_station)
                production_batches = production_wo.workorder_batch_ids
                production_check_lines = self.env['quality.check.production.line'].search([
                    ('workorder_batch_id', 'in', production_batches.ids)
                ])
                update_checks(production_check_lines, move.product_uom_qty, mrp_order.batches_count, move.product_id)

    def action_show_details(self):
        self.ensure_one()
        action = super().action_show_details()
        if self.raw_material_production_id:
            action['context']['upload_image'] = True
        return action

    def action_open_move_reserve_wizard(self):
        self.ensure_one()
        wizard = self.env['move.reserve.wizard'].create({
            'move_id': self.id,
            'move_reserve_wizard_line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'new_quantity': line.product_uom_qty,
                'lot_id': line.lot_id.id,
                'location_id': line.location_id.id,
                'package_id': line.package_id.id,
                'owner_id': line.owner_id.id,
            }) for line in self.move_line_ids]
        })
        view = self.env.ref('aznut_mrp.move_reserve_wizard_form')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Move Reserve Wizard',
            'view_mode': 'form',
            'res_model': 'move.reserve.wizard',
            'target': 'new',
            'view_id': view.id,
            'res_id': wizard.id,
        }

    def write(self, vals):
        res = super(StockMove, self).write(vals)
        if 'product_uom_qty' in vals:
            self._update_manufacturing_checks()
        return res


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    show_upload_lot_image_button = fields.Boolean(
        string='Show Upload Lot Image Button',
        compute='_compute_show_upload_lot_image_button'
    )

    @api.depends('lot_id')
    @api.depends_context('upload_image')
    def _compute_show_upload_lot_image_button(self):
        self.show_upload_lot_image_button = False
        if self.env.context.get('upload_image', False):
            for move_line in self.filtered(lambda mvl: mvl.lot_id):
                move_line.show_upload_lot_image_button = True

    def action_upload_lot_image(self):
        self.ensure_one()
        if self.lot_id:
            view = self.env.ref('aznut_mrp.upload_lot_image_wizard_form')

            return {
                'type': 'ir.actions.act_window',
                'name': 'Upload Lot Image',
                'view_mode': 'form',
                'res_model': 'upload.lot.image.wizard',
                'target': 'new',
                'view_id': view.id,
                'context': {
                    'default_lot_id': self.lot_id.id,
                }
            }
