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

from math import floor


def check_if_batch(order):
    return 1 < order.product_id.batch


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    batches_count = fields.Integer(
        string='Number Of Batches',
        compute='_compute_batches_count',
    )

    @api.depends('product_qty', 'product_id.batch')
    def _compute_batches_count(self):
        for order in self:
            if check_if_batch(order):
                order.batches_count = floor(order.product_qty / order.product_id.batch)
            else:
                order.batches_count = 0

    @api.constrains('qty_producing')
    def _check_qty_producing(self):
        for order in self:
            if check_if_batch(order):
                if order.qty_producing % order.product_id.batch != 0 and order.state == 'draft':
                    raise ValidationError(
                        _(f'You need to provide value that can be multiplied by {order.product_id.batch}'))

    # def _generate_backorder_productions(self, close_mo=True):
    #     backorders = super(MrpProduction, self)._generate_backorder_productions(close_mo=close_mo)
    #     for wo in backorders.workorder_ids:
    #         if 1 < wo.product_id.batch <= wo.qty_production:
    #             wo.qty_producing = wo.product_id.batch
    #     return backorders
