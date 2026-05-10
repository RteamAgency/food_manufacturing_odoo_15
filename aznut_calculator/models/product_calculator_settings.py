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
from odoo.exceptions import ValidationError

from .product_calculator import check_ingredients_is_unique


class ProductCalculatorSettings(models.Model):
    _name = 'product.calculator.settings'
    _description = 'Product Calculator Settings'

    @api.constrains('base_ingredient_ids')
    def _check_ingredients_is_unique(self):
        for rec in self:
            msg = check_ingredients_is_unique({'Base': 'base_ingredient_ids'}, rec)
            if msg:
                raise ValidationError('\n'.join(msg))

    @api.constrains('base_ingredients_quantity', 'readonly_active_ingredients_quantity', 'one_batch_lb')
    def _check_ingredients_quantity(self):
        for rec in self:
            if rec.base_ingredients_quantity and rec.readonly_active_ingredients_quantity and rec.one_batch_lb:
                if (rec.readonly_active_ingredients_quantity + rec.base_ingredients_quantity) != rec.one_batch_lb:
                    raise ValidationError('Quantity is not equal to One Batch LB')

    name = fields.Char(
        string='Name',
        required=True,
    )
    one_batch_lb = fields.Integer(
        string='One Batch LB',
        default=520,
        required=True,
        digits=(16, 3),
    )
    base_ingredient_ids = fields.Many2many(
        'base.ingredient',
        string='Base Ingredients',
    )
    base_ingredients_quantity = fields.Float(
        string='Base Ingredients Quantity',
        required=True,
    )
    readonly_active_ingredients_quantity = fields.Float(
        string='Active Ingredients Quantity',
        required=True,
    )
    bacteria_gram_base = fields.Integer(
        string='Bacteria grams base',
        default=10,
        required=True,
    )
    bacteria_gram_exponent = fields.Integer(
        string='Bacteria grams exponent',
        default=10,
        required=True,
    )
    lead_time = fields.Text(
        string='Lead Time',
    )
    box_preset = fields.Float(
        string='Box'
    )
    label_preset = fields.Float(
        string='Label',
    )
    shrink_preset = fields.Float(
        string='Shrink'
    )
    monthly_expenses_preset = fields.Integer(
        string='Monthly Expenses'
    )
    jar_per_months_preset = fields.Integer(
        string='Jars Per Month'
    )
    shipping_cost = fields.Float(
        string='Shipping cost',
    )
    profit = fields.Float(
        string='Profit',
    )
    taxes = fields.Float(
        string='Taxes',
        digits=(16, 2),
    )
    flavour_category_id = fields.Many2one(
        'product.category',
        string='Flavour Category',
    )
    dog_treats_packaging_materials_category_id = fields.Many2one(
        'product.category',
        string='Dog Treats Packaging Materials Category',
    )
    jar_products_ids = fields.Many2many(
        'product.product',
        string='Jar And Lid Products',
    )
    calculator_product_category_id = fields.Many2one(
        'product.category',
        string='Calculator Product Category',
    )
    auto_adjusted_base_ingredients_ids = fields.Many2many(
        'product.product',
        'auto_adjusted_base_ingredients_rel',
        string='Auto Adjusted Base Ingredients',
    )


class ProductShape(models.Model):
    _name = 'product.calculator.settings.shape'
    _description = 'Product Shape'

    name = fields.Char(
        string='Name',
        required=True,
    )
    color = fields.Integer(
        string='Color'
    )
    cost = fields.Float(
        string='Cost',
        default=1,
        required=True,
    )


class ProductCalculatorProfitGroup(models.Model):
    _name = 'product.calculator.profit.group'
    _description = 'Product Calculator Profit Group'

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Group Already Exists!"),
    ]

    @api.constrains('users_ids')
    def _check_users(self):
        for group in self:
            groups = self.env['product.calculator.profit.group'].search([
                ('id', '!=', group.id),
                ('users_ids', 'in', group.users_ids.ids),
            ])
            if groups:
                groups_users_list = ['%s - %s' % (i.name, ', '.join(i.users_ids.mapped('name'))) for i in groups]
                raise ValidationError(_('Group with these users: \n%s' % ',\n'.join(groups_users_list)))

    name = fields.Char(
        string='Name',
        required=True,
    )
    users_ids = fields.Many2many(
        'res.users',
        string='Users',
    )
    calculator_profit = fields.Float(
        string='Calculator Comission',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda rec: rec.env.ref('base.USD')
    )


class CalculatorMoqDiscount(models.Model):
    _name = 'product.calculator.moq.discount'
    _description = 'Calculator Moq Discount'

    divider = fields.Integer(
        string='Divider',
        required=True,
    )
    moq_discount = fields.Float(
        string='MOQ Discount',
        default=0
    )
