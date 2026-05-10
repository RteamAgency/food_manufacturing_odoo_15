from odoo import fields, models, api
from odoo.tools import float_compare

from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_join

from emoji import replace_emoji

from .product_category import _get_quantity_to_order, _get_data


def remove_emojis(text):
    return replace_emoji(text, replace='')


def get_link(record, menu_id, action_id):
    secondary_url = 'web#id=%s&menu_id=%s&action=%s&model=%s&view_type=form' % (
        record.id, menu_id, action_id, record._name
    )
    return url_join(record.get_base_url(), secondary_url)


def check_line(line, mode='out'):
    def check_in(ln):
        return ln.get('move_in') and ln.get('document_in')

    def check_main(ln):
        document_out = ln.get('document_out')
        return document_out._name == 'mrp.production' if document_out else False

    if mode == 'out':
        return check_main(line) and ((line.get('move_out') and not line.get('move_in')) or (check_in(line)))
    elif mode == 'in':
        return check_in(line)
    else:
        return check_main(line)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    on_the_way_quantity = fields.Float(
        related='product_variant_id.on_the_way_quantity',
        store=True,
    )
    three_months_average_consumed_quantity = fields.Float(
        related='product_variant_id.three_months_average_consumed_quantity',
        store=True,
    )
    turnover = fields.Float(
        related='product_variant_id.turnover',
        store=True,
    )
    lead_time_history_lines_ids = fields.Many2many(
        related='product_variant_id.lead_time_history_lines_ids',
    )
    free_qty = fields.Float(
        related='product_variant_id.free_qty',
    )

    def open_change_product_category_wizard(self):
        if self:
            wizard = self.env['change.product.category.wizard'].create({
                'wizard_line_ids': [(0, 0, {'product_template_id': product_tmpl.id}) for product_tmpl in self],
            })
            return {
                'name': 'Change Product Category',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'change.product.category.wizard',
                'view_id': self.env.ref('aznut_purchase.change_product_category_wizard_form').id,
                'target': 'new',
                'res_id': wizard.id,
            }

    def get_product_template_link(self):
        self.ensure_one()
        menu_id = self.env.ref('aznut_sale.menu_product_template').id
        action_id = self.env.ref('purchase.product_normal_action_puchased').id
        return get_link(self, menu_id, action_id)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _should_create_purchase_order(self):
        self.ensure_one()
        three_month_diff = fields.Datetime.today() - relativedelta(months=3)
        order_lines_count = self.env['purchase.order.line'].search_count([
            ('product_id', '=', self.id),
            ('create_date', '>=', three_month_diff),
        ])
        return False if order_lines_count < 2 else True

    on_the_way_quantity = fields.Float(
        string='On The Way Quantity',
        store=True,
    )
    three_months_average_consumed_quantity = fields.Float(
        string='Three Months Average Consumed Quantity',
        store=True,
    )
    turnover = fields.Float(
        string='Turnover',
        store=True,
    )
    components_not_available_quantity = fields.Float(
        string='Not Available Quantity',
        store=True,
    )
    components_on_the_way_quantity = fields.Float(
        string='On The Way Quantity',
        store=True,
    )
    components_no_po_quantity = fields.Float(
        string='No PO Quantity',
        store=True,
    )
    po_info = fields.Html(
        string='PO Info',
        store=True,
    )
    last_mo_date = fields.Date(
        string="Last MO"
    )
    lead_time_history_lines_ids = fields.Many2many(
        'lead.time.history.line',
        compute='_compute_lead_time_history_lines_ids',
    )

    def _compute_lead_time_history_lines_ids(self):
        for product in self:
            product.lead_time_history_lines_ids = product.mapped('seller_ids.lead_time_history_line_ids')

    def _cron_calculate_product_quantities(self):
        products = self.env['product.product'].search([])
        if not products:
            return
        quantities = products._compute_quantities_dict(False, False, False, fields.Date.today())
        average_quantities = _get_quantity_to_order(self.env['mrp.production'], products, 3, 'average')

        for product in products:
            three_months_average_consumed_quantity = (average_quantities[product.id] / 2) or 0
            on_the_way_quantity = quantities[product.id]['incoming_qty'] or 0
            if three_months_average_consumed_quantity:
                turnover = (product.virtual_available / three_months_average_consumed_quantity) or 0
            else:
                turnover = 0
            product.write({
                'on_the_way_quantity': on_the_way_quantity,
                'three_months_average_consumed_quantity': three_months_average_consumed_quantity,
                'turnover': turnover,
            })

    def _calculate_components_not_available(self):
        for product in self:
            data = _get_data(self, product)
            out_quantity = sum([line.get('quantity') for line in data if check_line(line, mode='out')])
            total_quantity = out_quantity - product.qty_available if (out_quantity - product.qty_available) > 0 else 0
            in_lines = [line for line in data if check_line(line, mode='in')]
            in_quantity = sum([line.get('quantity') for line in in_lines])

            li_items = []
            grouped = {}

            for line in in_lines:
                order = line.get('document_in', self.env['purchase.order'])
                order_name = remove_emojis(order.name or 'No Order')
                quantity = line.get('quantity', 0)
                date_str = line.get('receipt_date')
                uom = line.get('uom_id')

                if order_name in grouped:
                    grouped[order_name]['quantity'] += quantity
                else:
                    grouped[order_name] = {
                        'quantity': quantity,
                        'uom': uom.name if uom else '',
                        'date': date_str
                    }

            for order_name, vals in grouped.items():
                date_display = vals.get('date')
                li_items.append(
                    f"<li>{order_name} - {round(vals.get('quantity', 0), 2)} {vals.get('uom')} - {date_display}</li>")

            po_info_html = f"<ul>{''.join(li_items)}</ul>"
            not_available_qty = total_quantity
            on_the_way_qty = in_quantity
            no_po_qty = max(not_available_qty - on_the_way_qty, 0)

            latest_mrp_line = max(
                (
                    line for line in data
                    if line.get('document_out') and line.get('delivery_date')
                ),
                key=lambda line: line['delivery_date'],
                default=None
            )

            product.write({
                'components_not_available_quantity': not_available_qty,
                'components_on_the_way_quantity': on_the_way_qty,
                'po_info': po_info_html,
                'components_no_po_quantity': no_po_qty,
                'last_mo_date': latest_mrp_line.get('document_out').date_planned_start if latest_mrp_line else False,
            })

    def open_product(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current'
        }

    def get_product_link(self):
        self.ensure_one()
        menu_id = self.env.ref('aznut_sale.menu_product_product').id
        action_id = self.env.ref('purchase.product_product_action').id
        return get_link(self, menu_id, action_id)

    def action_product_product_forecast_report(self):
        ctx = {'default_product_tmpl_id': self.product_tmpl_id.id}
        return self.with_context(ctx).product_tmpl_id.action_product_tmpl_forecast_report()


class SellerLine(models.Model):
    _inherit = 'product.supplierinfo'

    lead_time_history_line_ids = fields.One2many(
        'lead.time.history.line',
        'seller_line_id',
        string='Lead Time History Lines',
        readonly=True,
        copy=False,
    )

    def action_open_lead_time_history(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lead Time History',
            'res_model': 'lead.time.history.line',
            'view_mode': 'tree',
            'domain': [('id', 'in', self.lead_time_history_line_ids.ids)],
            'target': 'new'
        }

    @api.model
    def create(self, vals):
        delay = vals.get('delay', 0)
        if delay:
            vals.update({'lead_time_history_line_ids': [(0, 0, {
                'old_delay': 0,
                'new_delay': delay,
                'date': fields.Datetime.now(),
                'partner_id': vals.get('partner_id', False),
            })]})
        return super(SellerLine, self).create(vals)

    def write(self, vals):
        new_delay = vals.get('delay', 0)
        if new_delay:
            for line in self:
                old_delay = line.delay
                if float_compare(new_delay, old_delay, precision_digits=2):
                    self.env['lead.time.history.line'].create({
                        'seller_line_id': line.id,
                        'new_delay': new_delay,
                        'old_delay': old_delay,
                        'date': fields.Datetime.now(),
                        'partner_id': vals.get('partner_id', False) or line.name.id,
                    })
        return super(SellerLine, self).write(vals)


class LeadTimeHistoryLine(models.Model):
    _name = 'lead.time.history.line'
    _description = 'Lead Time line'
    _order = 'date desc'

    date = fields.Datetime(
        string='Date',
        required=True,
    )
    old_delay = fields.Integer(
        string='Old Lead Time',
        required=True,
    )
    new_delay = fields.Integer(
        string='New Lead Time',
        required=True,
    )
    seller_line_id = fields.Many2one(
        'product.supplierinfo',
        string='Seller Line',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
    )
