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


def vendor_need_check(purchase_orders_without_check, frequency):
    if purchase_orders_without_check >= frequency:
        return True
    return False


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    quality_point_id = fields.Many2one(
        'quality.point',
        string='Quality Point',
        copy=False,
    )

    def button_confirm(self):
        for order in self:
            quality_point = self.env['quality.point'].search([
                ('measure_on', '=', 'vendor'),
                ('vendor_id', '=', order.partner_id.id)
            ])[:1]
            if quality_point:
                partner = order.partner_id
                if vendor_need_check(partner.purchase_orders_without_check, quality_point.purchase_orders_frequency):
                    order.quality_point_id = quality_point
                    partner.write({'purchase_orders_without_check': 0})
                else:
                    partner.write({'purchase_orders_without_check': partner.purchase_orders_without_check + 1})
        res = super(PurchaseOrder, self).button_confirm()
        return res

    def _prepare_picking(self):
        self.ensure_one()
        res = super(PurchaseOrder, self)._prepare_picking()
        if self.quality_point_id:
            res.update({'quality_point_id': self.quality_point_id.id})
        return res
