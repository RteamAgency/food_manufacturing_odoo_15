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


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    show_production_margin = fields.Boolean(
        string="Show Production Margin",
        copy=False,
    )
    production_margin = fields.Monetary(
        string="Production Margin",
        compute='_compute_production_margin',
        digits='Product Price',
        store=True,
        groups="base.group_user",
        copy=False,
    )
    production_margin_percent = fields.Float(
        string="Production Margin (%)",
        compute='_compute_production_margin',
        store=True,
        groups="base.group_user",
        group_operator="avg",
        copy=False,
    )
    hide_total_margin = fields.Boolean(
        string="Hide Total Margin",
        compute='_compute_hide_total_margin',
    )

    @api.depends('order_line.production_margin', 'amount_untaxed', 'show_production_margin')
    def _compute_production_margin(self):
        orders_without_margin = self.filtered(lambda so: not so.show_production_margin)
        orders_without_margin.production_margin = orders_without_margin.production_margin_percent = 0
        self = self - orders_without_margin
        if not all(self._ids):
            for order in self.filtered(lambda order: order.show_production_margin):
                order.production_margin = sum(order.order_line.mapped('production_margin'))
                order.production_margin_percent = order.amount_untaxed and order.production_margin / order.amount_untaxed
        else:
            self.env["sale.order.line"].flush(['production_margin'])
            grouped_order_lines_data = self.env['sale.order.line'].read_group(
                [
                    ('order_id', 'in', self.ids),
                ], ['production_margin', 'order_id'], ['order_id'])
            mapped_data = {m['order_id'][0]: m['production_margin'] for m in grouped_order_lines_data}
            for order in self:
                order.production_margin = mapped_data.get(order.id, 0.0)
                order.production_margin_percent = order.amount_untaxed and order.production_margin / order.amount_untaxed

    def _compute_hide_total_margin(self):
        self.hide_total_margin = self.env['ir.config_parameter'].sudo().get_param('aznut_mrp.hide_total_margin')

    def action_confirm(self):
        return super(SaleOrder, self.with_context(confirm_mo=False)).action_confirm()

    def _cron_sync_sale_orders_from_invoices(self):
        invoices = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('payment_state', '=', 'in_payment')
        ])
        for invoice_line in invoices.invoice_line_ids:
            invoice_line.sale_line_ids.write({'price_unit': invoice_line.price_unit})


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    production_margin = fields.Float(
        "Production Margin",
        compute='_compute_production_margin',
        digits='Product Price',
        store=True,
        groups="base.group_user",
        copy=False,
    )
    production_margin_percent = fields.Float(
        string="Production Margin (%)",
        compute='_compute_production_margin',
        store=True,
        group_operator='avg',
        copy=False,
    )
    production_purchase_price = fields.Float(
        string='Production Cost',
        digits='Product Price',
        copy=False,
        groups="base.group_user",
    )

    @api.depends('price_subtotal', 'product_uom_qty', 'production_purchase_price')
    def _compute_production_margin(self):
        for line in self:
            line.production_margin = line.price_subtotal - (line.production_purchase_price * line.product_uom_qty)
            line.production_margin_percent = line.price_subtotal and line.production_margin / line.price_subtotal
