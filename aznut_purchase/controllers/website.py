from odoo import http, SUPERUSER_ID
from odoo.http import request
from odoo.tools import float_compare

from re import compile


def validate_orders_date_planned(orders):
    for order in orders:
        date = order.order_line.sorted('date_planned', reverse=True)[:1].date_planned
        order.write({'date_planned': date})


def generate_name(current_order):
    def get_parent(order):
        if not order.parent_order_id:
            return order
        return get_parent(order.parent_order_id)

    parent_order = get_parent(current_order)
    parent_order.write({'seq_number': parent_order.seq_number + 1})
    return '%s-%s' % (parent_order.name, parent_order.seq_number)


def create_alternative_order(order):
    ProductOrder = request.env['purchase.order'].with_user(SUPERUSER_ID)
    OrderLine = request.env['purchase.order.line'].with_user(SUPERUSER_ID)

    suppliers = set(order.mapped('order_line.product_id.seller_ids.name')) - {order.partner_id}
    alternative_orders = order

    for supplier in suppliers:
        name = generate_name(order)
        new_order = ProductOrder.create({
            'partner_id': supplier.id,
            'user_id': order.user_id.id,
            'parent_order_id': order.parent_order_id.id,
            'name': name,
        })

        alternative_orders |= new_order

        relevant_lines = order.order_line.filtered(
            lambda l: supplier in l.product_id.seller_ids.mapped('name')
        )

        OrderLine.create([{
            'order_id': new_order.id,
            'product_id': line.product_id.id,
            'product_qty': line.product_qty,
        } for line in relevant_lines])

    for ao in alternative_orders:
        ao.write({
            'alternative_orders_ids': (alternative_orders - ao).ids,
        })


def update_alternative_orders(order):
    alternative_orders = order.alternative_orders_ids.filtered(lambda ao: not ao.supplier_confirmation_status)

    for main_line in order.order_line.filtered(lambda l: l.product_qty > 0):
        for ao in alternative_orders:
            remaining_qty = main_line.product_qty
            for line in ao.order_line.filtered(lambda l: l.product_id == main_line.product_id):
                if remaining_qty <= 0:
                    break
                elif remaining_qty >= line.product_qty:
                    remaining_qty -= line.product_qty
                    line.with_context(needed=True).unlink()
                else:
                    line.write({'product_qty': line.product_qty - remaining_qty})
                    remaining_qty = 0
    orders_to_delete = alternative_orders.filtered(lambda ao: not ao.order_line)
    orders_to_delete.button_cancel()
    orders_to_delete.unlink()


class AvailabilityConfirmationPage(http.Controller):
    @http.route(['/availability_confirmation'], type='http', auth='public', website=True)
    def availability_confirmation(self, access_token=None):
        order = request.env['purchase.order'].with_user(SUPERUSER_ID).search([('access_token', '=', access_token)],
                                                                             limit=1)
        if not order or not order.order_line or order.state == 'cancel':
            return request.render('aznut_purchase.availability_confirmation_not_found')
        elif order.supplier_confirmation_status in ['confirmed_by_supplier', 'not_in_stock']:
            return request.render('aznut_purchase.availability_confirmation_done')
        return request.render('aznut_purchase.availability_confirmation', {'order': order})

    @http.route('/confirm/availability', type='json', auth='public', methods=['POST'], csrf=True)
    def confirm_availability(self, **kwargs):
        data = request.jsonrequest
        order_id = data.get('order')
        lines_data = data.get('lines')
        comments = data.get('comments')
        success_response = {'message': 'Availability Confirmed!'}

        if not order_id or not lines_data:
            return {'message': 'Missing Data!'}

        PurchaseOrder = request.env['purchase.order'].with_user(SUPERUSER_ID)
        PurchaseOrderLine = request.env['purchase.order.line'].with_user(SUPERUSER_ID)

        order = PurchaseOrder.browse(int(order_id))
        new_lines = []

        if comments:
            order.message_post(body="Supplier Comments: %s" % comments)

        for item in lines_data:
            line = PurchaseOrderLine.browse(int(item['id']))
            qty = float(item.get('qty') or 0.0)
            availability = item.get('availability')
            date = item.get('date')

            if float_compare(qty, line.product_qty, precision_digits=2) == 0:
                line.write({'date_planned': date})
                continue

            diff = line.product_qty - qty

            vals = {
                'product_id': line.product_id.id,
                'qty': diff,
                'date': date,
                'remainder_date': item.get('remainder_date'),
            }

            if availability == 'out' or float_compare(diff, line.product_qty, precision_digits=2) == 0:
                line.with_context(needed=True).unlink()
            else:
                vals.update({'split': True})
                line.write({'product_qty': qty, 'date_planned': date})
            new_lines.append(vals)
        if order.order_line:
            order.write({'supplier_confirmation_status': 'confirmed_by_supplier'})

        update_alternative_orders(order)
        if not new_lines:
            validate_orders_date_planned(order)
            return success_response

        is_first_split = not order.order_line
        if is_first_split:
            order.write({'supplier_confirmation_status': 'not_in_stock'})
            new_order = order
        else:
            name = generate_name(order)
            new_order = PurchaseOrder.create({
                'partner_id': order.partner_id.id,
                'parent_order_id': order.id,
                'name': name,
                'user_id': order.user_id.id,
            })
        for l in new_lines:
            line_vals = {
                'order_id': new_order.id,
                'product_id': l['product_id'],
                'product_qty': l['qty'],
            }
            if not l.get('split'):
                date_planned = l['date']
            else:
                date_planned = l['remainder_date']
            if date_planned:
                line_vals.update({'date_planned': date_planned})
            PurchaseOrderLine.create(line_vals)
        create_alternative_order(new_order)
        validate_orders_date_planned(order | new_order)
        return success_response


class RequestForVendorPage(http.Controller):
    @http.route(['/request_for_vendor'], type='http', auth='public', website=True)
    def availability_confirmation(self, request_for_vendor_access_token=None):
        order = request.env['purchase.order'].with_user(SUPERUSER_ID).search(
            [('request_for_vendor_access_token', '=', request_for_vendor_access_token)], limit=1)
        if not order or not order.order_line or order.state == 'cancel':
            return request.render('aznut_purchase.request_for_vendor_not_found')
        elif order.is_eta_confirmed:
            return request.render('aznut_purchase.request_for_vendor_done')
        return request.render('aznut_purchase.request_for_vendor_main', {'order': order})

    @http.route('/confirm/request_for_vendor', type='http', auth='public', methods=['POST'], csrf=True)
    def confirm_availability(self, **kwargs):
        order_id = kwargs.get('order_id')

        if not order_id:
            return request.redirect('/request_for_vendor')

        PurchaseOrder = request.env['purchase.order'].sudo()
        order = PurchaseOrder.browse(int(order_id))
        pattern = compile(r"^date_(\d+)$")

        for key, value in kwargs.items():
            match = pattern.match(key)
            if match:
                line = order.order_line.filtered(lambda ln: ln.id == int(match.group(1)))
                line.sudo().write({'date_planned': value})
        order.write({'is_eta_confirmed': True})
        order.with_user(SUPERUSER_ID).message_post(body="Supplier Confirmed ETA")
        link = '/request_for_vendor?request_for_vendor_access_token=%s' % order.request_for_vendor_access_token
        return request.redirect(link)
