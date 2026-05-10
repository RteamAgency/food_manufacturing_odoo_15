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

colors = [0, 3, 4, 1, 2, 5, 6, 7, 8, 9, ]


class StockProductLot(models.Model):
    _inherit = "stock.production.lot"

    color = fields.Integer(
        string='Color Index',
        compute='_compute_color',
    )

    @api.depends_context('active_id')
    def _compute_color(self):
        self.color = 0
        for lot in self:
            if self._context.get('workorder_id'):
                workorder = self.env['mrp.workorder'].browse(self._context.get('workorder_id'))
                premix = workorder.production_id.workorder_ids.filtered(lambda wo: wo.premix_station)
                quality_check = premix.check_ids.filtered(lambda check: check.component_id == lot.product_id)[:1]
                lots_ids = quality_check.move_id.move_line_ids.sorted(
                    lambda line: line.lot_id == quality_check.workorder_id.lot_id, reverse=True).mapped('lot_id.id')
                if lot.id in lots_ids:
                    color_index = lots_ids.index(lot.id)
                else:
                    color_index = int(str(lot.id)[:1])
                if color_index > 9:
                    color_index = int(str(color_index)[:1])
                lot.color = colors[color_index]
            else:
                lot.color = int(str(lot.id)[:1])
