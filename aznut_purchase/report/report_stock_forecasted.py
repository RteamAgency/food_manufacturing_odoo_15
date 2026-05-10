from odoo import models
from ..models.product_category import _get_date_ranges
from ..models.product import get_link

from datetime import datetime

ACTION_DICT = {
    'sale.order': 'sale.action_orders',
    'mrp.production': 'mrp.mrp_production_action',
    'purchase.order': 'purchase.purchase_form_action'
}
MENU_DICT = {
    'sale.order': 'sale.menu_sale_order',
    'mrp.production': 'mrp.menu_mrp_root',
    'purchase.order': 'purchase.menu_purchase_root',
}


def _get_average_6_month_forecast(mrp_env, product_id, months_back=3):
    date_ranges = _get_date_ranges(months_back)
    mos = mrp_env.search([
        ('date_finished', '>=', date_ranges[-1][0]),
        ('date_finished', '<=', date_ranges[0][1]),
        ('state', '=', 'done')
    ])
    all_moves = mos.mapped('move_raw_ids').filtered(lambda mv: mv.product_id.id in product_id.ids)
    products_dict = {product_id: [] for product_id in product_id.ids}
    product_moves = all_moves.filtered(lambda mv: mv.product_id.id == product_id.id)
    product_mos = all_moves.mapped('raw_material_production_id')
    all_brands = product_mos.mapped('product_id.attribute_line_ids').filtered(
        lambda line: line.attribute_id.name == 'Brand')
    brand_names = set(all_brands.mapped('value_ids.name'))
    for date_start, date_end in date_ranges:
        consumed_quantity = sum(
            move.quantity_done for move in product_moves
            if date_start <= move.raw_material_production_id.date_finished.date() <= date_end
        )
        products_dict[product_id.id].append(consumed_quantity)
    return {key: sum(values) for key, values in products_dict.items() if values}, brand_names


class ReplenishmentReport(models.AbstractModel):
    _inherit = 'report.stock.report_product_product_replenishment'

    def _get_report_data(self, product_template_ids=False, product_variant_ids=False):
        res = super(ReplenishmentReport, self)._get_report_data(product_template_ids, product_variant_ids)
        product_id = False
        if product_template_ids:
            product_template_ids = self.env['product.template'].browse(product_template_ids)
            product_id = product_template_ids.product_variant_ids
        elif product_variant_ids:
            product_id = self.env['product.product'].browse(product_variant_ids)

        if len(product_id) == 1:
            average_three_month_consumed_quantity = product_id.three_months_average_consumed_quantity if product_id._should_create_purchase_order() else 0
            max_quantities, brands = _get_average_6_month_forecast(self.env['mrp.production'], product_id, 6)
            avg_monthly_consumed_quantity = (max_quantities[product_id.id] / 6) or 0
            free_qty_line = [line for line in res['lines'] if
                             not line.get('document_in') and not line.get('reservation') and line.get(
                                 'replenishment_filled') and not line.get('document_out')]
            delivery_date_lines = [line for line in res['lines'] if line.get('delivery_date')]

            res['three_months_average_consumed_quantity'] = average_three_month_consumed_quantity
            res['daily_use'] = average_three_month_consumed_quantity / 30
            res['avg_monthly_consumed_qty'] = avg_monthly_consumed_quantity
            res['brands'] = list(brands)
            sellers = dict()
            purchase_lines = self.env['purchase.order.line'].search([('product_id', '=', product_id.id)])
            for purchase_line in purchase_lines:
                for move in purchase_line.move_ids.filtered(lambda mv: mv.picking_id.date_done):
                    picking = move.picking_id
                    actual_lead_time = (picking.date_done - purchase_line.order_id.create_date).days
                    if actual_lead_time > 0:
                        if picking.partner_id.id not in sellers:
                            sellers.update({
                                picking.partner_id.id: {
                                    'actual_lead_time': [actual_lead_time],
                                    'price': [purchase_line.price_unit]
                                }
                            })
                        else:
                            record = sellers[picking.partner_id.id]
                            record['actual_lead_time'].append(actual_lead_time)
                            record['price'].append(purchase_line.price_unit)
            res['seller_lines'] = {k: {'actual_lead_time': int(sum(v['actual_lead_time']) / len(v['actual_lead_time'])),
                                       'price': round(sum(v['price']) / len(v['price']), 2)} for k, v in
                                   sellers.items()}
            res['free_qty'] = round(free_qty_line[0]['quantity'] if free_qty_line else 0, 2)
            if delivery_date_lines:
                last_delivery_date_str = delivery_date_lines[-1]['delivery_date']
                last_delivery_date_obj = datetime.strptime(last_delivery_date_str, '%m/%d/%Y').date()
                res['last_delivery_date'] = last_delivery_date_obj.strftime('%B %d, %Y')
        return res

    def _prepare_report_line(self, quantity, move_out=None, move_in=None, replenishment_filled=True, product=False,
                             reservation=False):
        def get_source_link(move):
            source_document = move._get_source_document()
            if source_document and source_document._name in ['mrp.production', 'purchase.order', 'sale.order']:
                menu_id = self.env.ref(MENU_DICT[source_document._name]).id
                action_id = self.env.ref(ACTION_DICT[source_document._name]).id
                return get_link(source_document, menu_id, action_id)
            return False

        res = super()._prepare_report_line(quantity, move_out, move_in, replenishment_filled, product, reservation)
        if move_in:
            res['in_source_document_link'] = get_source_link(move_in)
        if move_out:
            res['out_source_document_link'] = get_source_link(move_out)
        return res
