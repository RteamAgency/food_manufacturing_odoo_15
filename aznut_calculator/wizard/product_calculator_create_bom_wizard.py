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

from odoo import fields, models
from odoo.exceptions import ValidationError

from ..models.product_calculator import get_default


class CalculatorWizardMixin(models.AbstractModel):
    _name = 'calculator.wizard.mixin'
    _description = 'Calculator Wizard Mixin'

    create_bom_wizard_lines_ids = fields.Many2many(
        'create.bom.wizard.line',
        related='current_wizard_calculator_id.create_bom_wizard_lines_ids',
    )
    wizard_calculator_ids = fields.Many2many(
        'create.bom.wizard.product',
        relation='calculator_rel',
        string='Calculators',
    )
    suitable_wizard_calculators_ids = fields.One2many(
        'create.bom.wizard.product',
        'main_wizard_id',
        string='Suitable Calculators',
    )
    current_wizard_calculator_id = fields.Many2one(
        'create.bom.wizard.product',
        string="Current BOM"
    )
    routes_ids = fields.Many2many(
        'stock.location.route',
        default=lambda wizard: wizard.env.ref('mrp.route_warehouse0_manufacture')
    )

    def create_bom(self, bom_field):
        bom_ids = []

        if not self.wizard_calculator_ids:
            raise ValidationError('Please choose calculators for BoM creation')

        fields_list = ['uom_id', 'quantity', 'create_bom_wizard_lines_ids', 'product_tmpl_id']
        for wizard_calculator in self.wizard_calculator_ids:
            all_fields = wizard_calculator.fields_get()
            for field in fields_list:
                if hasattr(wizard_calculator, field) and not getattr(wizard_calculator, field):
                    field_string = all_fields.get(field, {}).get('string')
                    raise ValidationError(f'Missed field: {field_string} ({wizard_calculator.display_name})')

        for wizard_calculator in self.wizard_calculator_ids:
            wizard_calculator.calculator_id.write({
                'result_product_tmpl_id': wizard_calculator.product_tmpl_id.id
            })

            bom = self.env['mrp.bom'].sudo().create({
                'product_qty': wizard_calculator.quantity,
                'product_uom_id': wizard_calculator.uom_id.id,
                'product_tmpl_id': wizard_calculator.product_tmpl_id.id,
                bom_field: wizard_calculator.calculator_id.id,
            })

            for line in wizard_calculator.create_bom_wizard_lines_ids:
                self.env['mrp.bom.line'].sudo().create({
                    'product_id': line.product_id.id,
                    'product_qty': line.quantity,
                    'product_uom_id': line.uom_id.id,
                    'bom_id': bom.id,
                })

            bom_ids.append(bom.id)
        return bom_ids


class CreateBomWizardCalculatorMixin(models.AbstractModel):
    _name = 'create.bom.wizard.calculator.mixin'
    _description = 'Create BoM Wizard Calculator Mixin'

    calculator_id = fields.Many2one(
        'product.calculator',
        string='Calculator',
        required=True,
    )
    quantity = fields.Float(
        string='Quantity',
        default=1,
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        default=lambda rec: rec.env.ref('uom.product_uom_unit').id,
    )
    create_bom_wizard_lines_ids = fields.Many2many(
        'create.bom.wizard.line',
        string='Create BoM Wizard Lines',
        readonly=True,
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product',
    )
    main_wizard_id = fields.Many2one(
        'product.calculator.create.bom.wizard',
        string='Main Wizard',
        readonly=True,
    )

    def name_get(self):
        return [(wizard.id, wizard.calculator_id.product_name) for wizard in self]


class ProductCalculatorCreateBomWizard(models.TransientModel):
    _name = 'product.calculator.create.bom.wizard'
    _description = 'Product Calculator Create BoM Wizard'
    _inherit = 'calculator.wizard.mixin'

    calculator_product_category_id = fields.Many2one(
        'product.category',
        string='Calculator Product Category',
        default=lambda rec: get_default(rec, 'aznut_calculator.product_calculator_settings_main',
                                        'calculator_product_category_id'),
    )

    def action_confirm(self):
        self.ensure_one()
        tree_view_id = self.env.ref('mrp.mrp_bom_tree_view').id
        form_view_id = self.env.ref('mrp.mrp_bom_form_view').id
        bom_ids = self.create_bom('product_calculator_id')

        return {
            'name': 'BoMs',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.bom',
            'view_mode': 'tree, form',
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'domain': [('id', 'in', bom_ids)],
            'target': 'current',
        }


class PowderCalculatorCreateBomWizard(models.TransientModel):
    _name = 'powder.calculator.create.bom.wizard'
    _description = 'Powder Calculator Create BoM Wizard'
    _inherit = 'calculator.wizard.mixin'

    wizard_calculator_ids = fields.Many2many(
        'create.bom.wizard.powder',
        relation='powder_wizard_calculator_rel',
        string='Calculators',
    )
    suitable_wizard_calculators_ids = fields.One2many(
        'create.bom.wizard.powder',
        'main_wizard_id',
        string='Suitable Calculators',
    )
    current_wizard_calculator_id = fields.Many2one(
        'create.bom.wizard.powder',
        string="Current BOM"
    )
    calculator_product_category_id = fields.Many2one(
        'product.category',
        string='Calculator Powder Category',
        default=lambda rec: get_default(rec, 'aznut_calculator.powder_calculator_settings_main',
                                        'calculator_product_category_id'),
    )

    def action_confirm(self):
        self.ensure_one()
        tree_view_id = self.env.ref('mrp.mrp_bom_tree_view').id
        form_view_id = self.env.ref('mrp.mrp_bom_form_view').id
        bom_ids = self.create_bom('powder_calculator_id')

        return {
            'name': 'BoMs',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.bom',
            'view_mode': 'tree, form',
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'domain': [('id', 'in', bom_ids)],
            'target': 'current',
        }


class CreateBomWizardProduct(models.TransientModel):
    _name = 'create.bom.wizard.product'
    _description = 'Create BoM Wizard Product'
    _inherit = 'create.bom.wizard.calculator.mixin'


class CreateBomWizardPowder(models.TransientModel):
    _name = 'create.bom.wizard.powder'
    _description = 'Create BoM Wizard Powder'
    _inherit = 'create.bom.wizard.calculator.mixin'

    calculator_id = fields.Many2one(
        'powder.calculator',
        string='Calculator',
        required=True,
    )

    main_wizard_id = fields.Many2one(
        'powder.calculator.create.bom.wizard',
        string='Main Wizard',
        readonly=True,
    )


class CreateBomWizardLine(models.TransientModel):
    _name = 'create.bom.wizard.line'
    _description = 'Create BoM Wizard Line'

    quantity = fields.Float(
        string='Quantity',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Ingredient',
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
    )
