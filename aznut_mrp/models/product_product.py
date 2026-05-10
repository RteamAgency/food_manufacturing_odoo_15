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

from odoo.tools import float_compare


class ProductTemplate(models.Model):
    _inherit = "product.template"

    mrp_color = fields.Selection([
        ('1', 'Yellow'),
        ('2', 'Light Brown'),
        ('3', 'Red'),
        ('4', 'Dark')],
        string="MRP Color",
    )

    product_cost_history_line_ids = fields.Many2many(
        'product.cost.history.line',
        readonly=True,
        compute='_compute_product_cost_history_line_ids',
        string='Product Cost History History Lines',
    )
    is_customer_specific_labeling = fields.Boolean(
        string="Customer Specific Labeling",
    )
    pump_ratio = fields.Float(
        string="Pump Ratio",
        digits=(4, 3),
    )

    @api.onchange('sale_ok')
    def _onchange_sale_ok(self):
        if not self.sale_ok:
            self.is_customer_specific_labeling = False

    def _compute_product_cost_history_line_ids(self):
        for prd_tmpl in self:
            prd_tmpl.product_cost_history_line_ids = prd_tmpl.product_variant_ids.product_cost_history_line_ids


class ProductProduct(models.Model):
    _inherit = "product.product"

    product_cost_history_line_ids = fields.One2many(
        'product.cost.history.line',
        'product_id',
        readonly=True,
    )

    @api.model
    def create(self, vals):
        standard_price = vals.get('standard_price', 0)
        if standard_price:
            vals.update({'product_cost_line_ids': [(0, 0, {
                'old_standard_price': 0,
                'new_standard_price': standard_price,
                'date': fields.Datetime.now(),
            })]})
        return super(ProductProduct, self).create(vals)

    def write(self, vals):
        new_standard_price = vals.get('standard_price', 0)
        if new_standard_price:
            precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
            for product in self:
                old_standard_price = product.standard_price
                if float_compare(new_standard_price, old_standard_price, precision_digits=precision):
                    self.env['product.cost.history.line'].create({
                        'product_id': product.id,
                        'new_standard_price': new_standard_price,
                        'old_standard_price': old_standard_price,
                        'date': fields.Datetime.now(),
                    })
        return super(ProductProduct, self).write(vals)

    def _get_pump_uom(self, lb):
        self.ensure_one()
        return self.pump_ratio * lb if self.pump_ratio > 0 else False


class ProductCostLine(models.Model):
    _name = 'product.cost.history.line'
    _description = 'Product Cost History Line'
    _order = 'date desc'

    date = fields.Datetime(
        string='Date',
        required=True,
    )
    old_standard_price = fields.Float(
        string='Old Standard Price',
        company_dependent=True,
        digits='Product Price',
        groups='base.group_user',
        required=True,
    )
    new_standard_price = fields.Float(
        string='New Standard Price',
        company_dependent=True,
        digits='Product Price',
        groups='base.group_user',
        required=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product Template',
    )


class ProductCategory(models.Model):
    _inherit = 'product.category'

    is_removed_from_premix_availability = fields.Boolean(
        string='Removed From Premix Availability',
    )
