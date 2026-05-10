import binascii
from odoo import http, _, fields, SUPERUSER_ID
from odoo.http import request, content_disposition
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers import mail
from odoo.addons.portal.controllers.portal import pager as portal_pager, get_records_pager
from odoo.exceptions import AccessError, MissingError


class CustomerPortal(portal.CustomerPortal):

    def _get_quotes_searchbar_sortings(self):
        return {
            'date': {'label': _('Create Date'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }

    def _prepare_quotes_domain(self, partner):
        return [
            ('partner_id', '=', [partner.id]),
            ('state', 'in', ['sent', ])
        ]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        ProductCalculator = request.env['main.product.calculator']
        PowderCalculator = request.env['main.powder.calculator']
        if 'quotes_count' in counters:
            values['quotes_count'] = ProductCalculator.search_count(self._prepare_quotes_domain(partner)) \
                if ProductCalculator.check_access_rights('read', raise_exception=False) else 0
        if 'powder_quotes_count' in counters:
            values['powder_quotes_count'] = PowderCalculator.search_count(self._prepare_quotes_domain(partner)) \
                if PowderCalculator.check_access_rights('read', raise_exception=False) else 0
        return values

    @http.route(['/my/quotes_calc', '/my/quotes_calc/page/<int:page>', '/my/powder_quotes_calc',
                 '/my/powder_quotes_calc/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_quotes_calc(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        url = http.request.httprequest

        domain = self._prepare_quotes_domain(partner)

        searchbar_sortings = self._get_quotes_searchbar_sortings()

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if 'powder_quotes_calc' in url.base_url:
            Model = request.env['main.powder.calculator']
            pager_url = "/my/powder_quotes_calc"
            page_name = 'Powder Quote'
        else:
            Model = request.env['main.product.calculator']
            pager_url = "/my/quotes_calc"
            page_name = 'Quote'

        # count for pager
        quote_count = Model.search_count(domain)

        # make pager
        pager = portal_pager(
            url=pager_url,
            url_args={'sortby': sortby},
            total=quote_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        quotes = Model.search(domain, order=sort_order, offset=pager['offset'])
        request.session['my_quotations_history'] = quotes.ids[:100]

        values.update({
            'quotes': quotes,
            'page_name': page_name,
            'pager': pager,
            'default_url': pager_url,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("aznut_calculator_sign_quote.portal_my_quotes", values)

    @http.route(['/my/quotes_calc/<int:quote_id>', '/my/powder_quotes_calc/<int:quote_id>'], type='http', auth="user",
                website=True)
    def portal_quote_calc_page(self, quote_id, report_type=None, access_token=None, message=False, download=False,
                               **kw):
        url = http.request.httprequest.base_url
        if 'powder_quotes_calc' in url:
            model = 'main.powder.calculator'
            report_ref = 'aznut_calculator.action_report_main_product_calculator'
        else:
            model = 'main.product.calculator'
            report_ref = 'aznut_calculator.action_report_main_powder_calculator'

        try:
            quote_sudo = self._document_check_access(model, quote_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=quote_sudo, report_type=report_type, report_ref=report_ref,
                                     download=download)

        values = {
            'quote': quote_sudo,
            'message': message,
            'token': access_token,
            'bootstrap_formatting': True,
            'partner_id': quote_sudo.partner_id.id,
            'report_type': 'html',
        }
        if quote_sudo.company_id:
            values['res_company'] = quote_sudo.company_id

        return request.render('aznut_calculator_sign_quote.calculator_quote_portal_template', values)

    @http.route(['/my/quotes_calc/<int:quote_id>/accept', '/my/powder_quotes_calc/<int:quote_id>/accept'], type='json',
                auth="public", website=True)
    def portal_quotes_calc_accept(self, quote_id, access_token=None, name=None, signature=None):
        # get from query string if not on json param
        access_token = access_token or request.httprequest.args.get('access_token')
        url = http.request.httprequest.base_url
        if 'powder_quotes_calc' in url:
            model = 'main.powder.calculator'
            ref = 'aznut_calculator.action_report_main_powder_calculator'
            field = 'main_powder_calculator_id'
        else:
            model = 'main.product.calculator'
            ref = 'aznut_calculator.action_report_main_product_calculator'
            field = 'main_calculator_id'
        try:
            quote_sudo = self._document_check_access(model, quote_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _('Invalid quote.')}

        try:
            quote_sudo.write({
                'signed_by': name,
                'signed_on': fields.Date.today(),
                'signature': signature,
                'is_locked': True,
                'calculator_status': 'signed_by_customer',
            })
            request.env.cr.commit()
        except (TypeError, binascii.Error) as e:
            return {'error': _('Invalid signature data.')}

        pdf = request.env.ref(ref).with_user(
            SUPERUSER_ID)._render_qweb_pdf([quote_sudo.id])[0]
        if quote_sudo.lead_id and signature:
            won_stage_id = request.env['crm.stage'].search([('name', '=', 'Won')])
            sale_order = request.env['sale.order']
            quote_sudo.lead_id.write({
                'stage_id': won_stage_id.id
            })
            sale_order.create({
                'partner_id': quote_sudo.partner_id.id,
                'origin': quote_sudo.lead_id.name,
                'opportunity_id': quote_sudo.lead_id.id,
                field: quote_sudo.id,
            })
            quote_sudo.lead_id.message_post(body=('Quote signed by %s') % (name,),
                                            attachments=[('%s.pdf' % quote_sudo.name, pdf)])

        query_string = '&message=sign_ok'
        return {
            'force_refresh': True,
            'redirect_url': quote_sudo.get_portal_url(query_string=query_string),
        }

    @http.route(['/my/orders/<int:order_id>', ], type='http', auth='public', website=True)
    def portal_order_page(self, order_id=None, **post):
        picking_id = post.get('out_pdf')
        if picking_id:
            picking = request.env['stock.picking'].browse(int(picking_id))
            check_ids = picking.check_ids.filtered(lambda rec: rec.quality_state != 'none')
            if check_ids:
                template = request.env.ref('quality_control.quality_check_report')
                pdf_content = template.sudo()._render_qweb_pdf(check_ids.ids)[0]
                reporthttpheaders = [
                    ('Content-Type', 'application/pdf'),
                    ('Content-Length', len(pdf_content)),
                ]
                filename = "%s - Worksheet Report.pdf" % (picking.name)
                reporthttpheaders.append(('Content-Disposition', content_disposition(filename)))
                return request.make_response(pdf_content, headers=reporthttpheaders)
        response = super(CustomerPortal, self).portal_order_page(order_id=order_id, **post)
        return response


class PortalChatter(mail.PortalChatter):
    @http.route(['/mail/chatter_post'], type='json', methods=['POST'], auth='public', website=True)
    def portal_chatter_post(self, res_model, res_id, message, **kw):
        res = super(PortalChatter, self).portal_chatter_post(res_model, res_id, message, **kw)
        if res_model == 'main.product.calculator':
            calculator = request.env['main.product.calculator'].browse(res_id)
            if calculator.lead_id:
                calculator.lead_id.message_post(body=message, attachment_ids=kw.get('attachment_ids', []))
        if res_model == 'main.powder.calculator':
            calculator = request.env['main.powder.calculator'].browse(res_id)
            if calculator.lead_id:
                calculator.lead_id.message_post(body=message, attachment_ids=kw.get('attachment_ids', []))
        return res
