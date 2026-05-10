from odoo import models, fields, api
from collections import defaultdict

from datetime import timedelta

odoo_tag_colors = {
    1: "#F06050",
    2: "#F4A460",
    3: "#F7CD1F",
    4: "#6CC1ED",
    5: "#7C6BE3",
    6: "#EB7575",
    7: "#3C8DBC",
    8: "#273C75",
    9: "#E74C3C",
    10: "#2ECC71",
    11: "#9B59B6",
}


def get_confirmed_quantity(env, so_id):
    return sum(
        env.env['sale.order'].browse(so_id).picking_ids.filtered(lambda p:
                                                                 p.picking_type_code == 'outgoing' and
                                                                 any(state in p.move_lines.mapped(
                                                                     'state') for state in
                                                                     ['confirmed', 'waiting',
                                                                      'partially_available'])
                                                                 ).mapped('confirmed_quantity'))


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    client_available_sale_orders = fields.Many2many(
        'sale.order',
        string='Client Sale Orders',
        compute='_compute_client_sale_orders',
    )
    tags_history_line_ids = fields.One2many(
        'tag.history.line',
        'order_id',
        string='Tags History Lines',
        readonly=True,
        ondelete='cascade',
    )
    previous_tag_ids = fields.Many2many(
        'crm.tag',
        string='Previous Tags',
        compute='_compute_previous_tag_ids',
    )
    confirmed_by_client = fields.Boolean(
        string='Confirmed By Client',
    )
    customer_service_id = fields.Many2one(
        'res.users',
        string='Customer Service',
    )
    scheduled_pick_up_date = fields.Datetime(
        string='Manufacture Scheduled Date',
        compute='_compute_so_qty',
    )

    def _get_available_quantity(self, lines):
        orders = self.filtered(lambda order: set(order.mapped('order_line.product_id.id')) & set(lines.mapped('product_id.id')))
        pickings = orders.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing' and p.state not in ['draft', 'cancel', 'done'])
        moves = pickings.move_lines.filtered(
            lambda mv: sum(mv.move_line_ids.mapped('product_uom_qty')) - mv.quantity_done > 0)
        result = dict()

        for move in sorted(moves, key=lambda mv: mv.picking_id.sale_id.create_date):
            result.update({
                move.picking_id.sale_id.id: [{
                    'lot_name': ', '.join(move.move_line_ids.mapped('lot_id.name')) or 'Not Lot',
                    'quantity': sum(move.move_line_ids.mapped('product_uom_qty')) - move.quantity_done,
                }]
            }
            )
        return result

    def _get_total_available_quantity(self, lines):
        data = self.client_available_sale_orders._get_available_quantity(lines)
        return sum(entry['quantity'] for values in data.values() for entry in values)

    @api.onchange('customer_service_id')
    def _onchange_customer_service_id(self):
        self.message_subscribe(partner_ids=self.customer_service_id.partner_id.ids)

    def _compute_so_qty(self):
        self.scheduled_pick_up_date = False
        super(SaleOrder, self)._compute_so_qty()
        for order in self.filtered(lambda so: so.manufacture_scheduled_date):
            order.scheduled_pick_up_date = order.manufacture_scheduled_date + timedelta(days=7)
    def _compute_client_sale_orders(self):
        for order in self:
            sale_orders = self.search([
                ('partner_id', '=', order.partner_id.id),
            ])
            orders_dict = sale_orders._get_available_quantity(order.order_line)
            available_orders = [so.id for so in sale_orders if orders_dict.get(so.id)]
            order.client_available_sale_orders = available_orders

    @staticmethod
    def _get_tag_color(tag):
        return odoo_tag_colors.get(tag.color, '#FFFFFF')

    def _compare_tags(self, old_tags_dict):
        for order in self:
            old_tags = old_tags_dict.get(order.id)
            if order.tag_ids != old_tags:
                self.env['tag.history.line'].create({
                    'order_id': order.id,
                    'old_tag_ids': old_tags.ids,
                    'new_tag_ids': order.tag_ids.ids,
                })

    def _compute_previous_tag_ids(self):
        for order in self:
            last_history_line = order.tags_history_line_ids.sorted('create_date', reverse=True)[:1]
            order.previous_tag_ids = last_history_line.old_tag_ids

    def write(self, vals):
        if vals.get('tag_ids'):
            old_tags_dict = {order.id: order.tag_ids or self.env['tag.history.line'] for order in self}
            res = super(SaleOrder, self).write(vals)
            self._compare_tags(old_tags_dict)
            return res
        return super(SaleOrder, self).write(vals)

    @api.model
    def create(self, vals):
        orders = super(SaleOrder, self).create(vals)
        if vals.get('tag_ids'):
            old_tags_dict = {order.id: self.env['tag.history.line'] for order in orders}
            orders._compare_tags(old_tags_dict)
        return orders


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    manufactured_qty = fields.Float(
        string='Manufactured Qty',
        compute='_compute_manufactured_qty',
    )

    def _compute_manufactured_qty(self):
        data = self.env['procurement.group'].read_group([('sale_id', 'in', self.mapped('order_id.id'))],
                                                        ['ids:array_agg(id)'],
                                                        ['sale_id'])
        mrp_dict = dict()
        for item in data:
            procurement_groups = self.env['procurement.group'].browse(item['ids'])
            mrp_dict[item['sale_id'][0]] = \
                procurement_groups.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids \
                | procurement_groups.mrp_production_ids
        for line in self:
            mo_ids = mrp_dict.get(line.order_id.id, self.env['mrp.production'])
            need_mos = mo_ids.filtered(lambda mo: mo.state == 'done' and mo.product_id.id == line.product_id.id)
            line.manufactured_qty = sum(need_mos.mapped('qty_producing'))


class TagHistoryLine(models.Model):
    _name = 'tag.history.line'
    _description = 'Tag History Line'

    order_id = fields.Many2one(
        'sale.order',
        string='Order',
    )
    new_tag_ids = fields.Many2many(
        'crm.tag',
        'new_tag_rel',
        string='New Tags',
    )
    old_tag_ids = fields.Many2many(
        'crm.tag',
        'old_tag_rel',
        string='Old Tags',
    )
