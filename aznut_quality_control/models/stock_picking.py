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

from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    quality_point_id = fields.Many2one(
        'quality.point',
        string='Quality Point',
    )

    def _create_vendor_quality_check(self):
        check_vals_list = []
        for picking in self.filtered(lambda p: p.quality_point_id):
            picking_check_vals_list = picking.quality_point_id._get_vendor_quality_check_vals()
            for check_value in picking_check_vals_list:
                check_value.update({
                    'picking_id': picking.id,
                })
            check_vals_list += picking_check_vals_list
        self.env['quality.check'].sudo().create(check_vals_list)

    def _compute_check(self):
        for picking in self:
            todo = False
            fail = False
            checkable_products = picking.mapped('move_line_ids').mapped('product_id')
            for check in picking.check_ids:
                if check.quality_state == 'none' and (
                        check.product_id in checkable_products or check.measure_on == 'vendor'):
                    todo = True
                elif check.quality_state == 'fail':
                    fail = True
                if fail and todo:
                    break
            picking.quality_check_fail = fail
            picking.quality_check_todo = todo

    def check_quality(self):
        self.ensure_one()
        checkable_products = self.mapped('move_line_ids').mapped('product_id')
        checks = self.check_ids.filtered(
            lambda check: check.quality_state == 'none' and (
                    check.product_id in checkable_products or check.measure_on == 'vendor'))
        if checks:
            return checks.action_open_quality_check_wizard()
        return False

    def _check_for_quality_checks(self):
        quality_pickings = self.env['stock.picking']
        for picking in self:
            product_to_check = picking.mapped('move_line_ids').filtered(lambda ml: ml.qty_done != 0).mapped(
                'product_id')
            if picking.mapped('check_ids').filtered(
                    lambda qc: qc.quality_state == 'none' and (
                            qc.product_id in product_to_check or qc.measure_on == 'vendor')):
                quality_pickings |= picking
        return quality_pickings
