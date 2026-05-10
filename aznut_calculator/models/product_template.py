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

from .product_calculator import calculator_salesperson_search, calculator_salesperson_read_group


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    calculator_uom_id = fields.Many2one(
        'uom.uom',
        string='Calculator UoM',
        default=lambda rec: rec.env.ref('aznut_calculator.product_uom_mg', raise_if_not_found=False)
    )
    flavour_quantity = fields.Float(
        string='Flavour Quantity',
    )
    flavour_color = fields.Integer(
        string='Flavour Color'
    )
    is_flavour = fields.Boolean(
        string='Is Flavour',
        compute='_compute_is_flavour',
    )

    def _compute_is_flavour(self):
        chews_calculator_settings = self.env.ref('aznut_calculator.product_calculator_settings_main')
        self.is_flavour = False
        for prd_tmpl in self:
            category_id = prd_tmpl.categ_id.id
            if chews_calculator_settings.flavour_category_id.id == category_id:
                prd_tmpl.is_flavour = True

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self.env.context.get('calculator_products'):
            args = calculator_salesperson_search(self, args)
        return super(ProductTemplate, self)._search(args, offset, limit, order, count, access_rights_uid)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self.env.context.get('calculator_products'):
            domain = calculator_salesperson_read_group(self, domain)
        return super(ProductTemplate, self).read_group(domain, fields, groupby, offset, limit, orderby, lazy)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self.env.context.get('calculator_products'):
            args = calculator_salesperson_search(self, args)
        return super(ProductProduct, self)._search(args, offset, limit, order, count, access_rights_uid)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self.env.context.get('calculator_products'):
            domain = calculator_salesperson_read_group(self, domain)
        return super(ProductProduct, self).read_group(domain, fields, groupby, offset, limit, orderby, lazy)
