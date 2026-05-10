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

from odoo import fields, models, api


class CopyCalculatorMixin(models.AbstractModel):
    _name = 'copy.calculator.mixin'
    _description = 'Copy Calculator Mixin'

    product_id = fields.Many2one(
        'product.product',
        required=True,
        string='Product',
    )
    not_allowed_products_ids = fields.Many2many(
        'product.product',
        related='main_calculator_id.products_ids',
    )
    main_calculator_id = fields.Many2one(
        'main.product.calculator',
        string='Main Calculator',
        readonly=True,
        required=True,
    )
    allowed_calculator_ids = fields.Many2many(
        'product.calculator',
        related='main_calculator_id.allowed_calculators_ids',
    )
    calculator_product_category_id = fields.Many2one(
        'product.category',
        related='main_calculator_id.calculator_product_category_id',
    )
    ready_jar_cost = fields.Float(
        related='calculator_id.ready_jar_cost',
    )
    calculator_id = fields.Many2one(
        'product.calculator',
        string='Calculator To Copy',
        required=True,
    )
    active_ingredient_ids = fields.Many2many(
        'active.ingredient',
        compute='_compute_active_ingredient_ids',
    )
    readonly_active_ingredient_ids = fields.Many2many(
        'active.ingredient',
        compute='_compute_readonly_active_ingredient_ids',
    )
    include_bom = fields.Boolean(
        string='Include BoM',
    )
    bom_id = fields.Many2one(
        'mrp.bom',
        string='BoM'
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        related='product_id.product_tmpl_id',
        string='Product Template',
    )
    wizard_lines = fields.Many2many(
        'copy.product.calculator.line',
        string='BoM Lines',
        compute='_compute_wizard_lines',
        store=True,
    )

    @api.onchange('include_bom')
    def _onchange_include_bom(self):
        if not self.include_bom:
            self.bom_id = False

    @api.depends('calculator_id')
    def _compute_active_ingredient_ids(self):
        for wzrd in self:
            wzrd.active_ingredient_ids = wzrd.calculator_id.active_ingredient_ids.sorted('sequence')

    @api.depends('calculator_id')
    def _compute_readonly_active_ingredient_ids(self):
        for wzrd in self:
            wzrd.readonly_active_ingredient_ids = wzrd.calculator_id.readonly_active_ingredient_ids.sorted('sequence')

    @api.depends('bom_id')
    def _compute_wizard_lines(self):
        for wzrd in self:
            wzrd.wizard_lines = [(0, 0, {
                'product_id': bom_line.product_id.id,
                'quantity': bom_line.product_qty,
                'currency_id': wzrd.main_calculator_id.currency_id.id,
            }) for bom_line in wzrd.bom_id.bom_line_ids]


class CopyProductCalculatorWizard(models.TransientModel):
    _name = 'copy.product.calculator.wizard'
    _description = 'Copy Product Calculator Wizard'
    _inherit = 'copy.calculator.mixin'

    base_ingredient_ids = fields.Many2many(
        'base.ingredient',
        compute='_compute_base_ingredient_ids',
    )

    @api.depends('calculator_id')
    def _compute_base_ingredient_ids(self):
        for wzrd in self:
            wzrd.base_ingredient_ids = wzrd.calculator_id.base_ingredient_ids.sorted('sequence')

    def action_confirm(self):
        self.ensure_one()
        calculator = self.calculator_id.copy({
            'calculator_type': 'product',
            'product_id': self.product_id.id,
        })
        new_ingredient_ids = []
        if self.wizard_lines:
            for ingredient in self.wizard_lines:
                new_ingredient = self.env['active.ingredient'].create({
                    'product_id': ingredient.product_id.id,
                    'quantity': ingredient.quantity,
                    'calculator_id': calculator.id,
                })
                new_ingredient_ids.append(new_ingredient.id)
            calculator.write({
                'active_ingredient_ids': [(4, new_ingredient_id) for new_ingredient_id in new_ingredient_ids]
            })
        self.main_calculator_id.write({
            'products_ids': [(4, self.product_id.id)],
            'calculator_ids': [(4, calculator.id)],
            'active_calculator_id': calculator.id,
        })


class CopyPowderCalculatorWizard(models.TransientModel):
    _name = 'copy.powder.calculator.wizard'
    _description = 'Copy Powder Calculator Wizard'
    _inherit = 'copy.calculator.mixin'

    main_calculator_id = fields.Many2one(
        'main.powder.calculator',
    )
    allowed_calculator_ids = fields.Many2many(
        'powder.calculator',
        related='main_calculator_id.allowed_calculators_ids',
    )
    calculator_id = fields.Many2one(
        'powder.calculator',
    )
    active_ingredient_ids = fields.One2many(
        'powder.active.ingredient',
        related='calculator_id.active_ingredient_ids',
    )

    def action_confirm(self):
        self.ensure_one()
        calculator = self.calculator_id.copy({
            'product_id': self.product_id.id,
            'product_name': self.product_id.display_name,
        })
        new_ingredient_ids = []
        if self.wizard_lines:
            for ingredient in self.wizard_lines:
                new_ingredient = self.env['powder.active.ingredient'].create({
                    'product_id': ingredient.product_id.id,
                    'quantity': ingredient.quantity,
                    'powder_calculator_id': calculator.id,
                })
                new_ingredient_ids.append(new_ingredient.id)
        self.main_calculator_id.write({
            'products_ids': [(4, self.product_id.id)],
            'powder_calculator_ids': [(4, calculator.id)],
            'active_powder_calculator_id': calculator.id,
        })


class CopyProductCalculatorWizardLines(models.TransientModel):
    _name = 'copy.product.calculator.line'
    _description = 'Copy Product Calculator Wizard Lines'

    quantity = fields.Float(
        string='Quantity',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
    )
    cost_per_lb = fields.Float(
        string='Cost Per Lb',
        related='product_id.standard_price',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
    )
