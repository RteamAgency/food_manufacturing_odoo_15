from odoo import fields, models, api
from odoo.exceptions import ValidationError
from werkzeug.urls import url_join

from collections import defaultdict

from odoo.addons.aznut_mrp.models.mrp_workorder import categories_to_exclude


def get_unavailable_products(self, number):
    product_mo_dict = defaultdict(list)
    mos = self.env['mrp.production'].search([('state', '=', 'confirmed')])
    for mo in mos:
        moves = mo.move_raw_ids.filtered(lambda mv: mv.product_id.categ_id.name not in categories_to_exclude)
        unavailable_moves = [mv for mv in moves if mv.onhand_deficit]
        if len(unavailable_moves) == number:
            for mv in unavailable_moves:
                product_mo_dict[mv.product_id].append(mo.id)
    return product_mo_dict


class PurchaseAcceleratorWizard(models.TransientModel):
    _name = 'purchase.accelerator.wizard'
    _description = 'Purchase Accelerator Wizard'

    @api.constrains('components_number')
    def _check_components_number(self):
        for wizard in self:
            if wizard.components_number <= 0:
                raise ValidationError('Component Number Must Be Greater Than Zero!')

    components_number = fields.Integer(
        string='Number Of Components',
        default=1,
    )
    purchase_accelerator_wizard_lines_ids = fields.One2many(
        'purchase.accelerator.wizard.line',
        'wizard_id',
        string='Lines',
    )

    def action_confirm(self):
        self.ensure_one()
        result = get_unavailable_products(self, self.components_number)
        if not result:
            raise ValidationError('Nothing To Accelerate!')
        for key, vals in result.items():
            self.env['purchase.accelerator.wizard.line'].sudo().create({
                'product_id': key.id,
                'mrp_orders_ids': vals,
                'wizard_id': self.id,
            })
        context = {}
        if self.components_number > 1:
            context.update({'search_default_group_by_mrp_orders_ids': True})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Accelerator Lines',
            'view_mode': 'tree',
            'res_model': 'purchase.accelerator.wizard.line',
            'domain': [('id', 'in', self.purchase_accelerator_wizard_lines_ids.ids)],
            'target': 'current',
            'context': context,
        }


class PurchaseAcceleratorWizardLine(models.TransientModel):
    _name = 'purchase.accelerator.wizard.line'
    _description = 'Purchase Accelerator Wizard'
    _order = 'batches_quantity DESC'

    @staticmethod
    def prepare_html(orders, date_field, menu_id, action_id):
        li_items = []
        for order in orders:
            base_url = order.get_base_url()
            secondary_url = 'web#id=%s&menu_id=%s&action=%s&model=%s&view_type=form' % (
                order.id, menu_id, action_id, order._name
            )
            url = url_join(base_url, secondary_url)
            li_items.append(
                f"<li><a href='{url or '/'}' target='_blank'>{order.display_name} - {getattr(order, date_field) if hasattr(order, date_field) else 'No Date'}</a></li>")
        return f"<ul>{''.join(li_items)}</ul>"

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        readonly=True,
    )
    mrp_orders_ids = fields.Many2many(
        'mrp.production',
        string='Manufacturing Orders',
        readonly=True,
        required=True,
    )
    batches_quantity = fields.Integer(
        string='Batches Quantity',
        compute='_compute_batches_quantity',
        store=True,
    )
    mo_info = fields.Html(
        string='Mo Information',
        compute='_compute_mo_info',
    )
    wizard_id = fields.Many2one(
        'purchase.accelerator.wizard',
        string='Wizard',
    )
    po_info = fields.Html(
        string='Po Information',
        compute='_compute_po_info',
    )

    @api.depends('mrp_orders_ids.product_qty', 'mrp_orders_ids.product_id.batch')
    def _compute_batches_quantity(self):
        for line in self:
            line.batches_quantity = sum(line.mapped('mrp_orders_ids.batches_count'))

    @api.depends('mrp_orders_ids.date_planned_start')
    def _compute_mo_info(self):
        menu_id = self.env.ref('mrp.menu_mrp_root').id
        action_id = self.env.ref('mrp.mrp_production_action').id
        for line in self:
            line.mo_info = self.prepare_html(line.mrp_orders_ids, 'date_planned_start', menu_id, action_id)

    @api.depends('product_id.purchase_order_line_ids.date_planned')
    def _compute_po_info(self):
        menu_id = self.env.ref('purchase.menu_purchase_root').id
        action_id = self.env.ref('purchase.purchase_form_action').id
        for line in self:
            po_lines = line.product_id.purchase_order_line_ids.filtered(lambda ln: ln.order_id.state in ['purchase', 'done'] and ln.quantity_to_receive > 0).sorted('date_planned')
            po_orders = po_lines.mapped('order_id')
            line.po_info = self.prepare_html(po_orders, 'date_planned', menu_id, action_id)
