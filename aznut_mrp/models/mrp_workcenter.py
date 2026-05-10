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

from odoo import models, fields, api


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    hide_mark_as_done_button = fields.Boolean(
        string='Hide Mark As Done Button',
    )
    hide_mark_as_done_and_close_button = fields.Boolean(
        string='Hide Mark as Done and Close',
    )
    packaging_station = fields.Boolean(
        string='Packaging Station',
    )
    quality_station = fields.Boolean(
        string='Quality Station',
    )
    production_station = fields.Boolean(
        string='Production Station',
    )
    premix_station = fields.Boolean(
        string='Premix Station',
    )
    cutting_time = fields.Float(
        'Cutting Time',
        default=30.00,
    )
    production_area_cleaning_station = fields.Boolean(
        string='Production Area Cleaning Station',
    )
    production_area_cleaning_product = fields.Many2one(
        'product.product',
        string='Production Area Cleaning Product',
    )
    packaging_area_cleaning_station = fields.Boolean(
        string='Packaging Area Cleaning Station',
    )
    packaging_area_cleaning_product = fields.Many2one(
        'product.product',
        string='Packaging Area Cleaning Product',
    )

    @api.onchange('production_area_cleaning_station')
    def _onchange_production_area_cleaning_station(self):
        self.production_area_cleaning_product = False

    @api.onchange('packaging_area_cleaning_station')
    def _onchange_packaging_area_cleaning_station(self):
        self.packaging_area_cleaning_product = False

    def _area_cleaning(self, production, cleaning_type='packaging', ):
        if cleaning_type == 'production':
            area_cleaning_station = self.env['mrp.workcenter'].search([
                ('production_area_cleaning_station', '=', True),
                ('production_area_cleaning_product', '!=', False),
            ], limit=1)
            product = area_cleaning_station.production_area_cleaning_product
            date_field, field_to_map = 'production_cleaning_date', 'production_cleaning_order_id'
        else:
            area_cleaning_station = self.env['mrp.workcenter'].search([
                ('packaging_area_cleaning_product', '!=', False),
                ('packaging_area_cleaning_station', '=', True),
            ], limit=1)
            product = area_cleaning_station.packaging_area_cleaning_product
            date_field, field_to_map = 'packaging_cleaning_date', 'packaging_cleaning_order_id'

        bom = product.bom_ids[:1]

        if area_cleaning_station:
            mo = self.env['mrp.production'].search([
                ('state', 'not in', ['cancel', 'done']),
                (date_field, '=', fields.Date.today()),
            ], limit=1)
            if not mo:
                mo = self.env['mrp.production'].sudo().create({
                    'product_id': product.id,
                    'product_uom_id': product.uom_id.id,
                    'bom_id': bom.id,
                    date_field: fields.Date.today(),
                })
                if bom:
                    mo._onchange_bom_id()
                    mo._onchange_move_raw()
                    mo._onchange_workorder_ids()
            production.sudo().write({field_to_map: mo.id})
