from odoo import http, SUPERUSER_ID, _, fields
from odoo.http import request, content_disposition
from odoo.exceptions import AccessError, MissingError
from odoo.osv.expression import AND, OR
from odoo.addons.portal.controllers.portal import pager as portal_pager

from odoo.addons.portal.controllers import portal

from base64 import b64encode, b64decode
from markupsafe import Markup
from werkzeug.urls import url_join


def _get_qty_to_add(order, qty_data, files=False, main=False):
    qty_updates = {}
    pickings = order.client_available_sale_orders.picking_ids.filtered(
        lambda p: p.picking_type_code == 'outgoing' and p.state not in ['draft', 'cancel', 'done'])
    moves = pickings.move_lines.filtered(
        lambda mv: sum(mv.move_line_ids.mapped('product_uom_qty')) - mv.quantity_done > 0)
    for move in sorted(moves, key=lambda mv: mv.picking_id.sale_id.create_date):
        for line in move.move_line_ids.filtered(lambda ml: ml.product_uom_qty - ml.qty_done > 0):
            if qty_data <= 0:
                break
            qty_to_add = min(line.product_uom_qty - line.qty_done, qty_data)
            qty_updates[line] = qty_to_add
            qty_data -= qty_to_add
            if not move.picking_id.confirmed_by_client and main:
                move.picking_id.write({'confirmed_by_client': True})
                template = request.env.ref('aznut_portal.order_shipping_confirmation')
                if template:
                    template.sudo().send_mail(
                        move.picking_id.id,
                        notif_layout='mail.mail_notification_light',
                    )
    if files:
        for filedata in files:
            for picking in moves.mapped('picking_id'):
                encoded_file_data = b64encode(filedata.read())
                attachment = request.env['ir.attachment'].sudo().create({
                    'name': filedata.filename,
                    'type': 'binary',
                    'datas': encoded_file_data,
                    'mimetype': 'application/pdf',
                    'res_model': 'stock.picking',
                    'res_id': picking.id,
                    'uploaded_from_portal': True,
                })
                message_body = '<p>Document was uploaded by: %s</p>' % request.env.user.partner_id.display_name
                picking.message_post(body=message_body, attachment_ids=attachment.ids)
    return qty_updates


def get_report_http_headers(name, length):
    report_http_headers = [('Content-Type', 'application/pdf'), ('Content-Length', length),
                           ('Content-Disposition', content_disposition(name))]
    return report_http_headers


def get_pdf_content(attachment):
    download_content = b64decode(attachment.datas)
    report_http_headers = get_report_http_headers(attachment.name, len(download_content))
    return download_content, report_http_headers


def prepare_shipping_requests_domain(partner):
    return ['|', '|',
            ('partner_id', '=', partner.id),
            ('partner_id', 'parent_of', partner.id),
            ('partner_id', 'child_of', partner.id),
            ('confirmed_by_client', '=', True)
            ]


class CustomerPortal(portal.CustomerPortal):

    @http.route(['/get_qty_to_add'], type='json', auth='user', website=True)
    def get_qty_to_add(self, **kwargs):
        qta_data, order_id = kwargs.get('qty_data'), kwargs.get('order_id')
        if qta_data and order_id:
            orders = {}
            lines = _get_qty_to_add(request.env['sale.order'].sudo().browse(int(order_id)), int(qta_data), False, False)
            for line, value in lines.items():
                orders.setdefault(line.picking_id.sale_id, []).append(value)
            return {
                'data': {key.display_name: sum(value) for key, value in orders.items()}
            }
        return None

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        StockPicking = request.env['stock.picking']

        if 'shipping_requests_count' in counters:
            values['shipping_requests_count'] = StockPicking.sudo().search_count(
                prepare_shipping_requests_domain(partner))
        return values

    @staticmethod
    def _get_sale_searchbar_inputs():
        return {
            'ref': {'input': 'ref', 'label': Markup(_('Search <span class="nolabel"> (by Reference)</span>'))},
            'tag': {'input': 'tag', 'label': Markup(_('Search <span class="nolabel"> (by Tag)</span>'))},
        }

    @staticmethod
    def _get_shipping_requests_searchbar_sortings():
        return {
            'date': {'label': _('Create Date'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }

    @staticmethod
    def _get_sale_order_search_domain(search_in, search):
        search_domain = []
        if search_in == 'ref':
            search_domain = OR([search_domain, [('name', 'ilike', search)]])
        if search_in == 'tag':
            search_domain = OR([search_domain, [('tag_ids', 'ilike', search)]])
        return search_domain

    @http.route(['/my/shipping_request', '/my/shipping_request/page/<int:page>'], type='http',
                auth="user", website=True, )
    def portal_my_requests(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        StockPicking = request.env['stock.picking']

        domain = prepare_shipping_requests_domain(partner)

        searchbar_sortings = self._get_shipping_requests_searchbar_sortings()

        if not sortby:
            sortby = 'date'
        sort_order = ', '.join(['state asc', searchbar_sortings[sortby]['order']])

        requests_count = StockPicking.sudo().search_count(domain)

        pager = portal_pager(
            url='/my/shipping_request',
            url_args={'sortby': sortby},
            total=requests_count,
            page=page,
            step=self._items_per_page
        )
        requests = StockPicking.sudo().search(domain, order=sort_order, offset=pager['offset'])

        values.update({
            'requests': requests,
            'page_name': 'Shipping Requests',
            'pager': pager,
            'default_url': '/my/shipping_request',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("aznut_portal.portal_my_shipping_request", values)

    @http.route(['/my/orders/<int:order_id>', ], type='http', auth='public', website=True)
    def portal_order_page(self, order_id=None, **post):
        access_token = post.get('access_token')
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        mo_ids, attachment_id = post.get('mo_ids'), post.get('attachment_id')
        check_ids = post.get('check_ids')
        if mo_ids:
            template = request.env.ref('mrp.action_report_production_order')
            pdf_content, _ = template.with_user(SUPERUSER_ID)._render_qweb_pdf(eval(mo_ids))
            filename = "%s - Production Order.pdf" % order_sudo.display_name
            report_http_headers = get_report_http_headers(filename, len(pdf_content))
            return request.make_response(pdf_content, headers=report_http_headers)
        if attachment_id:
            attachment = request.env['ir.attachment'].sudo().browse(eval(attachment_id))
            download_content, report_http_headers = get_pdf_content(attachment)
            return request.make_response(download_content, headers=report_http_headers)
        if check_ids:
            template = request.env.ref('quality_control.quality_check_report')
            pdf_content, _ = template.with_user(SUPERUSER_ID)._render_qweb_pdf(eval(check_ids))
            filename = "%s - Delivery Document.pdf" % order_sudo.display_name
            report_http_headers = get_report_http_headers(filename, len(pdf_content))
            return request.make_response(pdf_content, headers=report_http_headers)
        return super(CustomerPortal, self).portal_order_page(order_id=order_id, **post)

    @http.route('/sale_order/confirm_order', type='http', auth='public', csrf=True, website=True, methods=['POST'])
    def sale_order_confirm(self, **kwargs):
        order = request.website.sale_get_order()
        if order:
            order.sudo().write({
                'confirmed_by_client': True,
            })
            template = request.env.ref('aznut_portal.website_order_confirmation')
            base_url = order.get_base_url()
            menu_id = request.env.ref('sale.sale_menu_root').id
            action_id = request.env.ref('sale.action_sale_order_form_view').id
            secondary_url = 'web#id=%s&menu_id=%s&action=%s&model=sale.order&view_type=form' % (
                order.id, menu_id, action_id
            )
            url = url_join(base_url, secondary_url)
            if template:
                template.with_context(order_url=url).sudo().send_mail(
                    order.id,
                    notif_layout='mail.mail_notification_light',
                )
        return request.redirect('/shop/cart')

    @http.route('/sale_order_add_quantity/submit', type='http', auth='public', website=True, csrf=True,
                methods=['POST'])
    def add_quantity_sale_order_submit(self, **kwargs):
        order_id = kwargs.get('order_id')
        qty_data = kwargs.get('output_input_hidden')
        qty_data = int(qty_data)

        link = f'/my/orders/{order_id}' if order_id else '/my/orders'

        if not (order_id and qty_data):
            return request.redirect(link)

        order = request.env['sale.order'].sudo().browse(int(order_id))
        files = request.httprequest.files.getlist('delivery_order_file_data_saved')
        lines = _get_qty_to_add(order, qty_data, files, True)
        for line, value in lines.items():
            line.write({
                'qty_done': line.qty_done + value,
            })
        return request.redirect(link)

    @http.route(['/my/orders', '/my/orders/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_orders(self, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='ref', **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        domain = self._prepare_orders_domain(partner)

        searchbar_sortings = self._get_sale_searchbar_sortings()
        searchbar_inputs = self._get_sale_searchbar_inputs()

        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        if search and search_in:
            domain = AND([domain, self._get_sale_order_search_domain(search_in, search)])

        order_count = SaleOrder.search_count(domain)
        pager = portal_pager(
            url="/my/orders",
            url_args={
                'sortby': sortby,
                'search_in': search_in,
                'search': search,
                'date_begin': date_begin,
                'date_end': date_end,
            },
            total=order_count,
            page=page,
            step=self._items_per_page
        )
        orders = SaleOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_orders_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders,
            'page_name': 'order',
            'pager': pager,
            'default_url': '/my/orders',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
        })
        return request.render("sale.portal_my_orders", values)

    @http.route('/sale_order/duplicate', type='http', auth='public', csrf=True, website=True, methods=['POST'])
    def duplicate_sale_order(self, **kwargs):
        duplicate_qty_data, order_id = kwargs.get('duplicate_qty_data'), kwargs.get('order_id')
        link = '/my/orders/%s' % order_id if order_id else '/my/orders'
        if duplicate_qty_data and order_id:
            so = request.env['sale.order'].sudo().browse(eval(order_id))
            so.sudo().copy({'order_line': [
                (0, 0, {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': eval(duplicate_qty_data),
                    'product_uom': line.product_uom.id,
                    'price_unit': line.price_unit,
                }) for line in so.order_line
            ]})
            return request.redirect(so.get_portal_url(query_string='&message=duplicate_done'))
        return request.redirect(link)
