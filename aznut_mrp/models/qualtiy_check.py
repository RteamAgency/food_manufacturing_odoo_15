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


from odoo import fields, models, api, _
from odoo.tools import float_is_zero

from odoo.exceptions import ValidationError


class QualityCheck(models.Model):
    _inherit = "quality.check"

    quality_check_premix_line_ids = fields.One2many(
        'quality.check.premix.line',
        'quality_check_id',
        string='Quality Check Premix Lines',
    )
    has_quality_check_premix_lines = fields.Boolean(
        string='Has Quality Check Premix Lines',
        compute='_compute_has_quality_check_premix_lines',
    )
    production_batches = fields.Boolean(
        string='Production Batches',
        related='point_id.production_batches',
    )
    workorder_batch_ids = fields.Many2many(
        'mrp.workorder.batch',
        string='Batches',
    )
    not_create_components = fields.Boolean(
        related='point_id.not_create_components',
        string='Do Not Create Components'
    )

    @api.depends('quality_check_premix_line_ids')
    def _compute_has_quality_check_premix_lines(self):
        for check in self:
            check.has_quality_check_premix_lines = bool(check.quality_check_premix_line_ids)

    def action_open_quality_check_premix_lines(self):
        self.ensure_one()
        view = self.env.ref('aznut_mrp.quality_check_premix_line_tree')
        return {
            'name': _('Premix Lines'),
            'view_mode': 'tree',
            'res_model': 'quality.check.premix.line',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False, 'edit': False},
            'domain': [('quality_check_id', '=', self.id)],
            'target': 'current',
            'view_id': view.id,
        }

    def action_return_to_the_production_workorder(self):
        workorder_id = self.env.context.get('workorder_id')
        if workorder_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.workorder',
                'views': [[self.env.ref('mrp_workorder.mrp_workorder_view_form_tablet').id, 'form']],
                'res_id': workorder_id,
                'target': 'fullscreen',
                'flags': {
                    'withControlPanel': False,
                    'form_view_initial_mode': 'edit',
                },
                'context': {
                    'from_production_order': True,
                    'active_id': workorder_id,
                    'workorder_id': workorder_id,
                },
            }

    def do_production_quality_check_pass(self):
        self.ensure_one()
        not_validate_lines = self.env['quality.check.production.line'].search([
            ('quality_check_id', '=', self.id),
            ('is_checked', '=', False),
        ])
        if not_validate_lines:
            raise ValidationError(_('You need to validate all lines for this check'))
        self.do_pass()


class QualityCheckLineMixin(models.AbstractModel):
    _name = 'quality.check.line.mixin'
    _description = 'Quality Check Line Mixin'

    quality_check_id = fields.Many2one(
        'quality.check',
        string='Quality Check',
    )
    is_checked = fields.Boolean(
        string='Checked'
    )
    quantity = fields.Float(
        string='Quantity',
    )
    component_id = fields.Many2one(
        'product.product',
        string='Component',
    )
    reserved_lots_ids = fields.Many2many(
        'stock.production.lot',
        'Reserved Lots',
        compute='_compute_reserved_lots_locations_quantities_pumps',
    )
    locations = fields.Char(
        string='Locations',
        compute='_compute_reserved_lots_locations_quantities_pumps'
    )
    quantities_by_lot = fields.Char(
        compute='_compute_reserved_lots_locations_quantities_pumps',
        string='Quantities by Lot',
    )
    display_quantity = fields.Char(
        compute='_compute_reserved_lots_locations_quantities_pumps',
        string='Quantity',
    )
    pump_uom = fields.Char(
        string="Pump qty",
        compute="_compute_reserved_lots_locations_quantities_pumps",
    )

    def _compute_reserved_lots_locations_quantities_pumps(self):
        lb_uom = self.env.ref('uom.product_uom_lb')
        self.pump_uom = False
        for line in self:
            if line._name == 'quality.check.premix.line':
                premix_check = line.quality_check_id
            else:
                premix = line.workorder_batch_id.workorder_id.production_id.workorder_ids.filtered(
                    lambda order: order.premix_station)
                premix_check = premix.check_ids.filtered(lambda check: check.component_id == line.component_id)
            lots, locations, quantities_by_lot, quantity_sum = line._get_reserve_lots()
            if premix_check.component_uom_id.id == lb_uom.id:
                value = line.component_id._get_pump_uom(quantity_sum or round(line.quantity, 2))
                if not float_is_zero(value, precision_digits=2):
                    line.pump_uom = '{:,.2f}'.format(value)
            line.reserved_lots_ids = lots
            line.locations = locations
            line.quantities_by_lot = quantities_by_lot
            line.display_quantity = quantities_by_lot or round(line.quantity, 2)

    def _get_reserve_lots(self):
        self.ensure_one()
        move_lines = self.quality_check_id.move_id.move_line_ids.sorted(
            lambda line: line.lot_id == self.quality_check_id.workorder_id.lot_id, reverse=True)
        quality_check_premix_line_ids = self.quality_check_id.quality_check_premix_line_ids.ids
        if isinstance(self.id, int):
            line_id = self.id
        else:
            line_id = self.id.origin
        order = quality_check_premix_line_ids.index(line_id)
        remaining_quantity = self.quantity
        previous_reserved = order * self.quantity
        reserved_lots = self.env['stock.production.lot']
        locations = self.env['stock.location']
        quantities = []

        for move_line in move_lines:
            if move_line.state == 'done':
                uom_qty = move_line.qty_done
            else:
                uom_qty = move_line.product_uom_qty
            if previous_reserved >= uom_qty:
                previous_reserved -= uom_qty
                continue

            available_quantity = uom_qty - previous_reserved
            if available_quantity >= remaining_quantity:
                reserved_lots |= move_line.lot_id
                locations |= move_line.location_id
                quantities.append(str(round(remaining_quantity, 2)))
                remaining_quantity = 0
            else:
                reserved_lots |= move_line.lot_id
                locations |= move_line.location_id
                quantities.append(str(round(available_quantity, 2)))
                remaining_quantity -= available_quantity

            previous_reserved = 0

            if remaining_quantity == 0:
                break
        quantities_str = False
        if quantities:
            quantities_str = ', '.join(quantities)
        return reserved_lots, ', '.join(locations.mapped('display_name')), quantities_str, sum(
            map(lambda qty: float(qty), quantities))

    def _get_weight(self):
        self.ensure_one()
        lb_uom = self.env.ref('uom.product_uom_lb')
        move_id = self.quality_check_id.move_id
        quantity = sum(map(lambda qty: float(qty), self.display_quantity.split(', ')))
        return move_id.product_uom._compute_quantity(quantity, lb_uom, False, 'HALF-UP', False)

    def action_validate(self):
        self.ensure_one()
        self.is_checked = True

    def action_reset(self):
        self.ensure_one()
        self.is_checked = False


class QualityCheckPremixLine(models.Model):
    _name = 'quality.check.premix.line'
    _description = 'Quality Check Premix Line'
    _inherit = ['quality.check.line.mixin']

    component_id = fields.Many2one(
        'product.product',
        related='quality_check_id.component_id',
    )
    container_number = fields.Integer(
        string='Container #',
        store=True,
    )


class QualityCheckProductionLine(models.Model):
    _name = 'quality.check.production.line'
    _description = 'Quality Check Production Line'
    _inherit = ['quality.check.line.mixin']

    workorder_batch_id = fields.Many2one(
        'mrp.workorder.batch',
        string='Batch',
    )
    quality_check_name = fields.Char(
        related='quality_check_id.name',
        string='Reference',
    )

    def _get_reserve_lots(self):
        self.ensure_one()
        premix = self.workorder_batch_id.workorder_id.production_id.workorder_ids.filtered(
            lambda order: order.premix_station)
        premix_check = premix.check_ids.filtered(lambda check: check.component_id == self.component_id)
        production = self.workorder_batch_id.workorder_id.production_id.workorder_ids.filtered(
            lambda order: order.production_station)
        move_lines = premix_check.move_id.move_line_ids.sorted(
            lambda line: line.lot_id == premix_check.lot_id, reverse=True)
        quality_check_line_ids = self.env['quality.check.production.line'].search([
            ('workorder_batch_id', 'in', production.workorder_batch_ids.ids),
            ('component_id', '=', self.component_id.id),
        ]).ids
        if isinstance(self.id, int):
            line_id = self.id
        else:
            line_id = self.id.origin
        order = quality_check_line_ids.index(line_id)
        remaining_quantity = self.quantity
        previous_reserved = order * self.quantity
        reserved_lots = self.env['stock.production.lot']
        locations = self.env['stock.location']
        quantities = []

        for move_line in move_lines:
            if move_line.state == 'done':
                uom_qty = move_line.qty_done
            else:
                uom_qty = move_line.product_uom_qty
            if previous_reserved >= uom_qty:
                previous_reserved -= uom_qty
                continue

            available_quantity = uom_qty - previous_reserved
            if available_quantity >= remaining_quantity:
                reserved_lots |= move_line.lot_id
                locations |= move_line.location_id
                quantities.append(str(round(remaining_quantity, 2)))
                remaining_quantity = 0
            else:
                reserved_lots |= move_line.lot_id
                locations |= move_line.location_id
                quantities.append(str(round(available_quantity, 2)))
                remaining_quantity -= available_quantity

            previous_reserved = 0

            if remaining_quantity == 0:
                break
        quantities_str = False
        if quantities:
            quantities_str = ', '.join(quantities)
        return reserved_lots, ', '.join(locations.mapped('display_name')), quantities_str, sum(
            map(lambda qty: float(qty), quantities))

    def action_validate(self):
        time_now = fields.Datetime.now()
        super(QualityCheckProductionLine, self).action_validate()
        lines = self.env['quality.check.production.line'].search([
            ('quality_check_id', '=', self.quality_check_id.id),
            ('workorder_batch_id', '=', self.workorder_batch_id.id),
        ])
        if not lines.filtered(lambda line: not line.is_checked):
            batch_check = self.env['mrp.workorder.batch.check'].search([
                ('production_check_id', '=', self.quality_check_id.id),
                ('workorder_batch_id', '=', self.workorder_batch_id.id),
            ], limit=1)
            if not batch_check.time_finish:
                batch_check.time_finish = time_now
            batch_check.is_validated = True
        else:
            batch_check = self.env['mrp.workorder.batch.check'].search([
                ('production_check_id', '=', self.quality_check_id.id),
                ('workorder_batch_id', '=', self.workorder_batch_id.id),
            ], limit=1)
            batch_check.is_validated = False
