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


class ProductTemplate(models.Model):
    _inherit = "product.template"

    batch = fields.Integer(
        string='Batch'
    )

    _sql_constraints = [
        ('check_batch', 'check(batch >= 0)',
         'Batch should be positive!')
    ]

    def open_add_brand_wizard(self):
        attributes = self.env['product.attribute'].search([])
        brand_lines = attributes.filtered(lambda attribute: attribute.name.lower() == 'brand')
        allowed_attributes = brand_lines
        return {
            'name': 'Add Brand',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'add.brand.wizard',
            'view_id': self.env.ref('aznut_sale.add_brand_wizard_form').id,
            'target': 'new',
            'context': {
                'default_products_ids': self.ids,
                'default_allowed_attributes_ids': allowed_attributes.ids,
            }
        }
