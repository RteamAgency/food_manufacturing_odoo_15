from datetime import timedelta

from odoo import fields, models

from math import ceil

from dateutil.relativedelta import relativedelta


def _get_data(self, product):
    product.ensure_one()
    Report = self.env['report.stock.report_product_product_replenishment']
    warehouse = self.env['stock.warehouse'].browse(Report.get_warehouses()[0]['id'])

    wh_location_ids = [loc['id'] for loc in self.env['stock.location'].search_read(
        [('id', 'child_of', warehouse.view_location_id.id)],
        ['id'],
    )]
    lines = Report._get_report_lines(False, product.ids, wh_location_ids)
    return lines


def get_domain(category_id):
    return [('categ_id', '=', category_id)]


def get_adjusted_values(self, product, quantity):
    def round_to_package(qty, package_size):
        return ceil(qty / package_size) * package_size

    packaging = product.packaging_ids[:1]
    seller = product.seller_ids.sorted('sequence')[:1]
    delay_days = seller.delay if seller else 0
    adjusted_date = fields.Datetime.now() + timedelta(days=delay_days)

    if packaging:
        package_qty = packaging.qty
        adjusted_quantity = round_to_package(quantity, package_qty)
        average_consumption = _get_quantity_to_order(
            self.env['mrp.production'], product, months_back=3, mode='average'
        ).get(product.id, 0) / 60

        if average_consumption > 0 and delay_days > 0:
            extra_qty = adjusted_quantity - quantity
            extra_days = ceil(extra_qty / average_consumption)
            adjusted_date += timedelta(days=extra_days)

        return adjusted_quantity, adjusted_date

    return quantity, adjusted_date


def _get_date_ranges(months_back):
    current_date = fields.Date.today()
    return [
        (
            (current_date - relativedelta(months=i)).replace(day=1),
            (current_date - relativedelta(months=i - 1)).replace(day=1) - relativedelta(days=1)
        )
        for i in range(1, months_back + 1)
    ]


def _get_quantity_to_order(mrp_env, product_ids, months_back=3, mode='max'):
    date_ranges = _get_date_ranges(months_back)
    mos = mrp_env.search([
        ('date_finished', '>=', date_ranges[-1][0]),
        ('date_finished', '<=', date_ranges[0][1]),
        ('state', '=', 'done')
    ])
    all_moves = mos.mapped('move_raw_ids').filtered(lambda mv: mv.product_id.id in product_ids.ids)

    products_dict = {product_id: [] for product_id in product_ids.ids}
    for product_id in product_ids.ids:
        product_moves = all_moves.filtered(lambda mv: mv.product_id.id == product_id)
        for date_start, date_end in date_ranges:
            consumed_quantity = sum(
                move.quantity_done for move in product_moves
                if date_start <= move.raw_material_production_id.date_finished.date() <= date_end
            )
            products_dict[product_id].append(consumed_quantity)
    if mode == 'max':
        return {key: max(values, default=0) * 2 for key, values in products_dict.items() if values}
    else:
        return {key: (sum(values) / len(values)) * 2 for key, values in products_dict.items() if values}


def _get_quantity_actual(products):
    current_date = fields.Date.today()
    first_date = fields.Date.to_date('%s-%s-%s' % (current_date.year, current_date.month, 1))
    quantities = products._compute_quantities_dict(False, False, False, first_date, False)
    return {
        product.id: product.free_qty + quantities.get(product.id, {}).get('incoming_qty', 0)
        for product in
        products}


def _get_quantity_ordered(po_env, products):
    purchase_orders = po_env.search([
        ('is_ingredients_reordering_rule', '=', True),
        ('state', 'in', ['draft', 'sent', 'to approve']),
    ])
    order_lines = purchase_orders.mapped('order_line').filtered(lambda line: line.product_id.id in products.ids)
    return {product.id: sum(order_lines.filtered(lambda line: line.product_id.id == product.id).mapped('product_qty'))
            for product in products}


def _get_vendors_per_product(Move, products):
    domain_move_in_loc = products._get_domain_locations()[1]

    current_date = fields.Date.today()
    first_date = fields.Date.to_date('%s-%s-%s' % (current_date.year, current_date.month, 1))

    domain_move_in = domain_move_in_loc
    domain_move_in += [('date', '>=', first_date)]
    domain_move_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_in
    products_dict = {}

    for product in products:
        seller_line = product.seller_ids.sorted('sequence')[:1]
        if seller_line:
            domain_move_todo += [('product_id', '=', product.id)]
            moves_in_res = Move.search(domain_move_todo)
            delay = seller_line.delay or 0
            po_date = moves_in_res.mapped('purchase_line_id.order_id').sorted('date_planned', reverse=True)[
                      :1].date_planned
            if po_date:
                po_delay = po_date.day - fields.date.today().day
                delay = max([po_delay, delay])
            products_dict[product.id] = [seller_line.name.id, delay]
        else:
            error_str = 'Cannot execute Ingredients Reordering Rule (No Vendor)'
            product.message_post(body=error_str)
            product.product_tmpl_id.message_post(body=error_str)
    return products_dict


class ProductCategory(models.Model):
    _inherit = 'product.category'

    is_ingredients_reordering_rule = fields.Boolean(
        string='Ingredients Reordering Rule',
        readonly=True,
    )
    archived_reordering_rules_ids = fields.Many2many(
        'stock.warehouse.orderpoint',
        string='Archived Reordering Rules',
        context={'active_test': False},
    )

    def action_deactivate_ingredients_reordering_rule(self):
        self.filtered('is_ingredients_reordering_rule').mapped(
            'archived_reordering_rules_ids'
        ).write({'active': True})
        self.write({'is_ingredients_reordering_rule': False})

    def action_activate_ingredients_reordering_rule(self):
        for category in self.filtered(lambda cat: not cat.is_ingredients_reordering_rule):
            products = self.env['product.product'].search(get_domain(category.id))
            reordering_rules = self.env['stock.warehouse.orderpoint'].search([('product_id', 'in', products.ids)])
            category.write({
                'archived_reordering_rules_ids': [(6, 0, reordering_rules.ids)],
                'is_ingredients_reordering_rule': True,
            })
            reordering_rules.write({'active': False})

    def _cron_create_purchase_orders_for_ingredients_reordering_rule(self):
        suitable_categories = self.search([('is_ingredients_reordering_rule', '=', True)])
        products = self.env['product.product'].search([('categ_id', 'in', suitable_categories.ids)]).filtered(
            lambda prd: prd._should_create_purchase_order())
        quantity_to_order_dict = _get_quantity_to_order(self.env['mrp.production'], products, 3, 'average')
        quantity_actual_dict = _get_quantity_actual(products)
        quantity_ordered_dict = _get_quantity_ordered(self.env['purchase.order'], products)
        vendors_per_product = _get_vendors_per_product(self.env['stock.move'], products)

        for product_id, vendor_vals in vendors_per_product.items():
            product = self.env['product.product'].browse(product_id)
            vendor_id, delay = vendor_vals[0], vendor_vals[1]
            to_order_quantity = quantity_to_order_dict.get(product_id, 0)
            actual_quantity = quantity_actual_dict.get(product_id, 0)
            ordered_quantity = quantity_ordered_dict.get(product_id, 0)
            result_quantity = round(
                to_order_quantity - actual_quantity - ordered_quantity + (to_order_quantity / 60 * delay), 2)

            if result_quantity > 0:
                adjusted_quantity, adjusted_date = get_adjusted_values(self, product, result_quantity)
                po = self.env['purchase.order'].search([
                    ('partner_id', '=', vendor_id),
                    ('state', 'in', ['draft', 'sent', 'to approve']),
                    ('is_ingredients_reordering_rule', '=', True),
                ], limit=1)
                if not po:
                    po = self.env['purchase.order'].create({
                        'partner_id': vendor_id,
                        'is_ingredients_reordering_rule': True,
                    })
                if po.date_planned and po.date_planned < adjusted_date:
                    po.write({'date_planned': adjusted_date})
                po_line = po.order_line.filtered(lambda line: line.product_id.id == product_id)[:1]
                if po_line:
                    po_line.write({'product_qty': po_line.product_qty + adjusted_quantity})
                else:
                    self.env['purchase.order.line'].create({
                        'product_id': product_id,
                        'order_id': po.id,
                        'product_qty': adjusted_quantity,
                    })
