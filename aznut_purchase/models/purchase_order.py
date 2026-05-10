from odoo import fields, models, api, SUPERUSER_ID
from odoo.exceptions import ValidationError

from secrets import token_urlsafe
from werkzeug.urls import url_join
from re import match
from datetime import timedelta

from odoo.addons.aznut_mrp.models.mrp_workorder import categories_to_exclude
from ..models.product_category import _get_date_ranges
from ..models.product import remove_emojis


def get_mail_compose_message_action(self, name, partner_ids, body, res_id, model, subject, context=None):
    if context is None:
        context = {}
    mail_compose_message = self.env['mail.compose.message'].create({
        'body': body,
        'subject': subject,
        'partner_ids': partner_ids,
        'res_id': res_id,
        'model': model,
        'auto_delete': False,
        'use_active_domain': False,
        'active_domain': False,
    })
    return {
        'name': name,
        'type': 'ir.actions.act_window',
        'res_model': 'mail.compose.message',
        'view_mode': 'form',
        'target': 'new',
        'res_id': mail_compose_message.id,
        'context': context
    }


def get_purchase_order_action(name, records_ids):
    return {
        'type': 'ir.actions.act_window',
        'name': name,
        'view_mode': 'tree,form',
        'res_model': 'purchase.order',
        'domain': [('id', 'in', records_ids)],
        'target': 'current',
        'context': {
            'create': 0,
        }
    }


def get_nearest_line(po):
    return min(po.order_line, key=lambda line: abs(line.date_planned - po.date_planned))


def get_mos_availability_data(self):
    self = self.sudo()

    def is_valid_move(move):
        return (move.state not in {'done', 'cancel'}
                and move.product_id.categ_id.name not in categories_to_exclude)

    mos = self.env['mrp.production'].search([('state', '=', 'confirmed')], order='reservation_state')
    available_mos = self.env['mrp.production']
    not_available_products = self.env['product.product']

    all_moves = [mv for mo in mos for mv in mo.move_raw_ids if is_valid_move(mv)]
    products = {mv.product_id for mv in all_moves}
    products_on_hand = {p.id: p.qty_available for p in products}

    for mo in mos:
        available = True
        for mv in mo.move_raw_ids:
            if not is_valid_move(mv):
                continue
            pid = mv.product_id.id
            products_on_hand[pid] -= mv.product_uom_qty
            if products_on_hand[pid] < 0:
                not_available_products |= mv.product_id
                available = False
        if available:
            available_mos |= mo

    return {
        'not_available_mos': mos - available_mos,
        'not_available_products': not_available_products,
        'available_mos': available_mos,
    }


def get_quantity(po):
    lines = po.order_line
    return sum(lines.mapped('qty_received')), sum(lines.mapped('product_qty'))


MONTH_DICT = {
    '1': 'January',
    '2': 'February',
    '3': 'March',
    '4': 'April',
    '5': 'May',
    '6': 'June',
    '7': 'July',
    '8': 'August',
    '9': 'September',
    '10': 'October',
    '11': 'November',
    '12': 'December',
}


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _default_access_token(self):
        return token_urlsafe(32)

    is_ingredients_reordering_rule = fields.Boolean(
        string='Is Ingredients Reordering Rule',
    )
    qty_received = fields.Float(
        string='Quantity Received',
        compute='_compute_quantities'
    )
    qty_ordered = fields.Float(
        string='Quantity Ordered',
        compute='_compute_quantities'
    )
    supplier_mails_state = fields.Selection(
        [('availability_confirmation_mail_sent', 'Availability Confirmation Mail Sent'),
         ('shipping_information_request_mail_sent', 'Shipping Information Request Mail Sent'),
         ('confirmation_to_supplier_mail_send', 'Confirmation To Supplier Mail Sent')],
        string='Supplier Mails State',
        copy=False,
    )
    access_token = fields.Char(
        string='Access Token',
        default=_default_access_token,
        readonly=True,
    )
    supplier_confirmation_status = fields.Selection(
        [('not_in_stock', 'Not In Stock'),
         ('confirmed_by_supplier', 'Confirmed By Supplier'),
         ('waiting_for_confirmation', 'Waiting For Confirmation')],
        string='Confirmed By Vendor',
        readonly=True,
        copy=False,
    )
    parent_order_id = fields.Many2one(
        'purchase.order',
        string='Parent Order',
        copy=False,
    )
    child_orders_ids = fields.Many2many(
        'purchase.order',
        'children_order_rel',
        string='Children Orders',
        compute='_compute_child_orders_ids',
    )
    alternative_orders_ids = fields.Many2many(
        'purchase.order',
        'alternative_order_rel',
        'order_id',
        'alternative_order_id',
        string='Alternative Orders',
        copy=False,
    )
    linked_orders_ids = fields.Many2many(
        'purchase.order',
        'linked_order_rel',
        'order_id',
        'linked_order_id',
        string='Linked Orders',
        copy=False,
    )
    seq_number = fields.Integer(
        default=0,
        copy=False,
    )
    shipping_information = fields.Selection(
        [('waiting_for_shipping_information', 'Waiting For Shipping Information'),
         ('ready_to_schedule_shipments', 'Ready To Schedule Shipments'),
         ('in_transit', 'In Transit')],
        default='waiting_for_shipping_information',
        required=True,
        copy=False,
        string='Shipping Information',
    )
    seven_days_notice = fields.Selection(
        [('red', 'Red'), ('green', 'Green')],
        string='Seven Days Notice Technical',
        copy=False,
    )
    seven_days_notice_display = fields.Integer(
        string='Seven Days Notice',
        compute='_compute_seven_days_notice_display',
        store=True,
    )
    request_for_vendor_access_token = fields.Char(
        string='Request For Vendor Access Token',
        default=_default_access_token,
        readonly=True,
    )
    is_eta_confirmed = fields.Boolean(
        string='Is ETA Confirmed',
    )
    hide_for_receiving_operator = fields.Boolean(
        string='Hide for Receiving Operator',
        compute='_compute_hide_for_receiving_operator',
    )
    is_shipped = fields.Boolean(
        store=True,
    )

    @api.depends('seven_days_notice')
    def _compute_seven_days_notice_display(self):
        for po in self:
            if po.seven_days_notice == 'red':
                po.seven_days_notice_display = 1
            elif po.seven_days_notice == 'green':
                po.seven_days_notice_display = 10
            else:
                po.seven_days_notice_display = 0

    def _compute_quantities(self):
        for po in self:
            po.qty_received, po.qty_ordered = get_quantity(po)

    def _compute_child_orders_ids(self):
        for po in self:
            po.child_orders_ids = self.env['purchase.order'].search([('parent_order_id', '=', po.id)])

    def _compute_hide_for_receiving_operator(self):
        self.hide_for_receiving_operator = False
        for po in self:
            if self.env.user.has_group('aznut_purchase.group_receiving_operator'):
                if po.is_shipped or po.state not in ['purchase', 'done'] or po.incoming_picking_count == 0:
                    po.hide_for_receiving_operator = True

    @api.model
    def retrieve_dashboard(self):
        result = super(PurchaseOrder, self).retrieve_dashboard()
        data = get_mos_availability_data(self)

        total_jars_current, total_jars_next = self.get_total_jars_forecast()
        result.update({
            'waiting_for_shipping_information_count': self.env['purchase.order'].search_count(
                [('shipping_information', '=', 'waiting_for_shipping_information')]),
            'ready_to_schedule_shipments_count': self.env['purchase.order'].search_count(
                [('shipping_information', '=', 'ready_to_schedule_shipments')]),
            'in_transit_count': self.env['purchase.order'].search_count([('shipping_information', '=', 'in_transit')]),
            'available_batches': sum(data.get('available_mos', self.env['mrp.production']).mapped('batches_count')),
            'not_available_batches': sum(
                data.get('not_available_mos', self.env['mrp.production']).mapped('batches_count')),
            'current_month': {"avg": round(total_jars_current, 2),
                              "month": MONTH_DICT.get(str(fields.Date.today().month))},
            'next_month': {"avg": round(total_jars_next, 2),
                           "month": MONTH_DICT.get(str(fields.Date.today().month + 1))},
            'is_receiving_operator': self.env.user.has_group('aznut_purchase.group_receiving_operator'),
        })
        return result

    @api.model
    def generate_not_available_components(self):
        data = get_mos_availability_data(self)
        products = data.get('not_available_products', self.env['product.product'])
        products._calculate_components_not_available()
        return {'action': {
            'view_id': self.env.ref('aznut_purchase.product_product_tree_view_not_available').id,
            'domain': [('id', 'in', products.ids)]
        }}

    def action_run_ingredients_reordering_rule(self):
        self._check_receiving_operator()
        self.env['product.category']._cron_create_purchase_orders_for_ingredients_reordering_rule()

    def action_request_for_vendor(self):
        self._check_receiving_operator()
        delta_datetime = fields.Datetime.now() - timedelta(days=7)
        orders = self.env['purchase.order'].search([
            ('date_planned', '>=', delta_datetime),
            ('state', '=', 'purchase'),
            ('is_eta_confirmed', '=', False),
        ]).filtered(lambda po: sum(po.mapped('order_line.quantity_to_receive')) > 0)
        if not orders:
            raise ValidationError('No Orders Found!')

        wizard = self.env['request.for.vendor.wizard'].create({
            'request_for_vendor_wizard_line_ids': [(0, 0, {'order_id': order.id}) for order in orders],
        })
        return self.env['request.for.vendor.wizard'].get_wizard_action(wizard)

    def action_manager_review(self):
        self._check_receiving_operator()
        self.write({'seven_days_notice': False})

    def get_body(self, body):
        self.ensure_one()
        if '%name%' in body:
            body = body.replace('%name%', self.partner_id.name or '')
        if '%link%' in body:
            link = url_join(self.get_base_url(), 'availability_confirmation?access_token=%s' % self.access_token)
            body = body.replace('%link%', link or '')
        if '%order%' in body:
            body = body.replace('%order%', self.display_name or '')
        return remove_emojis(body)

    def action_send_availability_confirmation(self):
        self.ensure_one()
        template = self.env['ir.config_parameter'].sudo().get_param('aznut_purchase.vendor_availability_email_template')
        return get_mail_compose_message_action(self, 'Availability Confirmation', self.partner_id.ids,
                                               self.get_body(template), self.id, 'purchase.order',
                                               '%s Availability Confirmation' % self.display_name or 'Order',
                                               {'availability_confirmation_mail': True})

    def action_send_availability_confirmation_mass(self):
        self._check_receiving_operator()
        template = self.env['ir.config_parameter'].sudo().get_param('aznut_purchase.vendor_availability_email_template')
        for order in self:
            if not order.supplier_confirmation_status:
                body = order.get_body(template)
                self.env['mail.compose.message'].with_context(availability_confirmation_mail=True).create({
                    'body': body,
                    'subject': '%s Availability Confirmation' % order.display_name or 'Order',
                    'partner_ids': order.partner_id.ids,
                    'res_id': order.id,
                    'model': 'purchase.order',
                }).action_send_mail()

    def action_send_shipping_information_request(self):
        self.ensure_one()
        template = self.env['ir.config_parameter'].sudo().get_param(
            'aznut_purchase.shipping_information_request_email_template')
        return get_mail_compose_message_action(self, 'Shipping Information Request', self.partner_id.ids,
                                               self.get_body(template), self.id, 'purchase.order',
                                               '%s Shipping Information Request' % self.display_name or 'Order',
                                               {'shipping_information_request_mail': True})

    def action_send_confirmation_to_supplier(self):
        self.ensure_one()
        template = self.env['ir.config_parameter'].sudo().get_param(
            'aznut_purchase.confirmation_to_supplier_email_template')
        return get_mail_compose_message_action(self, 'Confirmation Request', self.partner_id.ids,
                                               self.get_body(template), self.id, 'purchase.order',
                                               '%s Confirmation Request' % self.display_name or 'Order',
                                               {'confirmation_to_supplier_mail': True})

    def action_open_parent_order(self):
        self.ensure_one()
        return get_purchase_order_action('Parent Order', self.parent_order_id.ids)

    def action_open_child_orders(self):
        self.ensure_one()
        return get_purchase_order_action('Child Orders', self.child_orders_ids.ids)

    def action_open_alternative_order(self):
        self.ensure_one()
        return get_purchase_order_action('Alternative Orders', self.alternative_orders_ids.ids)

    def action_open_linked_order(self):
        return get_purchase_order_action('Linked Orders', self.linked_orders_ids.ids)

    def button_confirm(self):
        for order in self.filtered(lambda po: po.supplier_confirmation_status == 'confirmed_by_supplier'):
            if match(r'^.+-\d+$', order.name):
                order.name = self.env['ir.sequence'].next_by_code('purchase.order') or order.name
            sorted_lines = sorted(order.order_line, key=lambda l: l.date_planned, reverse=True)

            groups = []
            current_group = []

            for line in sorted_lines:
                if not current_group:
                    current_group.append(line)
                else:
                    if all(abs((line.date_planned - other.date_planned).days) < 2 for other in current_group):
                        current_group.append(line)
                    else:
                        groups.append(current_group)
                        current_group = [line]

            if current_group:
                groups.append(current_group)

            if len(groups) <= 1:
                continue
            linked_orders = order
            common_vals = {
                'partner_id': order.partner_id.id,
                'user_id': order.user_id.id,
                'parent_order_id': order.parent_order_id.id,
                'supplier_confirmation_status': order.supplier_confirmation_status,
                'supplier_mails_state': order.supplier_mails_state,
            }

            for grp in groups[1:]:
                new_order = self.env['purchase.order'].create(common_vals)
                linked_orders |= new_order
                for line in grp:
                    self.env['purchase.order.line'].create({
                        'order_id': new_order.id,
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'product_qty': line.product_qty,
                        'price_unit': line.price_unit,
                        'date_planned': line.date_planned,
                        'product_uom': line.product_uom.id,
                        'taxes_id': [(6, 0, line.taxes_id.ids)],
                    })
                    line.unlink()
                new_order.button_confirm()
            for po in linked_orders:
                po.write({'linked_orders_ids': (linked_orders - po).ids})
        return super(PurchaseOrder, self).button_confirm()

    def get_total_jars_forecast(self):
        date_ranges = _get_date_ranges(3)
        last_three_month_mos = self.env['mrp.production'].sudo().search([
            ('date_finished', '>=', date_ranges[-1][0]),
            ('date_finished', '<=', date_ranges[0][1]),
            ('state', '=', 'done'), ('product_id.categ_id.name', 'ilike', 'Dog Treats')
        ])
        total_jars_current = sum(last_three_month_mos.mapped('qty_produced')) / 3
        next_month_ratio = float(self.env['ir.config_parameter'].sudo().get_param('aznut_purchase.jars_forecast_ratio'))
        total_jars_next = total_jars_current * next_month_ratio
        return total_jars_current, total_jars_next

    def _check_receiving_operator(self):
        if self.env.user.has_group('aznut_purchase.group_receiving_operator'):
            raise ValidationError('Receiving Operator is not allowed to perform this action.')


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    quantity_to_receive = fields.Float(
        string='Quantity To Receive',
        compute='_compute_quantity_to_receive',
    )

    def _compute_quantity_to_receive(self):
        for pol in self:
            quantity_to_receive = pol.product_qty - pol.qty_received
            pol.quantity_to_receive = quantity_to_receive if quantity_to_receive > 0 else 0

    def unlink(self):
        for line in self:
            if line.order_id and not self.env.context.get('needed'):
                line.order_id.message_post(
                    body=f"Order line deleted by {self.env.user.name or ''}: {line.name}"
                )
        return super().unlink()
