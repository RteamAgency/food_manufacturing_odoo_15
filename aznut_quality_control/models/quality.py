################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2024 SmartTek (<https://smartteksas.com>).
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


class QualityPoint(models.Model):
    _inherit = 'quality.point'

    @api.constrains('vendor_id', 'measure_on')
    def _check_quality_point_is_unique_per_vendor(self):
        for point in self:
            if point.measure_on == 'vendor' and point.vendor_id:
                suitable_points = self.env['quality.point'].search([
                    ('vendor_id', '=', point.vendor_id.id),
                    ('measure_on', '=', 'vendor'),
                ])
                if suitable_points - point:
                    raise ValidationError(_('Vendor Quality Point Should Be Unique Per Vendor!'))

    measure_on = fields.Selection(
        selection_add=[('vendor', 'Vendor')],
        ondelete={'vendor': 'cascade'},
    )
    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
    )
    purchase_orders_frequency = fields.Integer(
        string='Purchase Orders Frequency',
    )

    @api.onchange('measure_on')
    def _onchange_measure_on(self):
        self.product_category_ids = self.measure_frequency_value = self.measure_frequency_unit_value = False
        self.measure_frequency_type, self.measure_frequency_unit, self.product_ids = 'all', 'day', False
        self.picking_type_ids = self.vendor_id = False
        if self.measure_on == 'vendor':
            return {'domain': {'picking_type_ids': [('code', '=', 'incoming')]}}

    def _get_vendor_quality_check_vals(self):
        point_values = []
        product = self.env.ref('aznut_quality_control.product_product_vendor_quality_check_product')
        for point in self:
            point_values.append({
                'point_id': point.id,
                'team_id': point.team_id.id,
                'product_id': product.id,
                'measure_on': 'vendor',
            })
        return point_values


class QualityCheck(models.Model):
    _inherit = 'quality.check'

    measure_on = fields.Selection(
        selection_add=[('vendor', 'Vendor')],
        ondelete={'vendor': 'cascade'},
    )
