from odoo import api, fields, models

from odoo.exceptions import ValidationError

from ..models.recall import RECALL_DICT, RECALL_CLASSES


def get_mail_compose_wizard(record, view=True):
    recall_id = record.env.context.get('recall_id')

    if not recall_id:
        raise ValidationError("Not enough data!")

    recall = record.env['recall.recall'].browse(recall_id)
    recall_class_description = RECALL_DICT.get(recall.recall_class)
    recall_class = 'Class'
    if recall.recall_class == 'first_class':
        recall_class += ' I'
    elif recall.recall_class == 'second_class':
        recall_class += ' II'
    elif recall.recall_class == 'third_class':
        recall_class += ' III'

    res = record.env['mail.compose.message'].create({
        'model': 'sale.order',
        'res_id': record.id,
        'composition_mode': 'comment',
        'partner_ids': record.partner_id.ids,
        'template_id': record.env.ref('aznut_complaint_claim.recall_mail_template').id,
    })
    groups = record.env['procurement.group'].search([('sale_id', '=', record.id)])
    mos = groups.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids | groups.mrp_production_ids
    manufacture_dates = [mo.date_finished.strftime('%Y-%m-%d') for mo in mos if mo.date_finished]
    lots_expiration_dates = [mo.lot_producing_id.expiration_date.strftime('%Y-%m-%d') for mo in mos if
                             mo.lot_producing_id.expiration_date]
    product_names = ', '.join(mos.mapped('product_id.name'))
    recall_subject = 'URGENT: Product Recall Notification'
    lots_formatted = ['Lot #%s' % lot.name for lot in mos.mapped('lot_producing_id') if lot]
    if product_names or lots_formatted:
        lots_formatted = ['Lot #%s' % lot.name for lot in mos.mapped('lot_producing_id') if lot]
        title_list = [product_names or '', ', '.join(lots_formatted) or '']
        recall_subject += ' - %s' % ', '.join(title_list)

    res.with_context(
        products_names=product_names,
        partner_name=record.partner_id.name,
        lots_names=', '.join(lots_formatted),
        manufacture_dates=', '.join(manufacture_dates) if manufacture_dates else False,
        recall_class=recall_class,
        lots_expirations=', '.join(lots_expiration_dates) if lots_expiration_dates else False,
        recall_class_description=recall_class_description,
        recall_subject=recall_subject,
    )._onchange_template_id_wrapper()
    if view:
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'res_id': res.id,
            'target': 'new',
            'context': {
                'mark_as_sent': True,
                'custom_layout': "mail.mail_notification_light",
                'force_email': True,
            },
        }
    else:
        return res


def send_recall_mail(orders):
    for order in orders:
        res = get_mail_compose_wizard(order, view=False)
        res.action_send_mail()


class RecallWizard(models.TransientModel):
    _name = 'recall.wizard'
    _description = 'Recall Wizard'

    recall_class = fields.Selection(
        RECALL_CLASSES,
        string='Recall Class',
        required=True,
        default='first_class',
    )
    lot_id = fields.Many2one(
        'stock.production.lot',
        string='Lot',
    )
    allowed_production_ids = fields.Many2many(
        'mrp.production',
        compute='_compute_allowed_production_ids',
    )
    production_id = fields.Many2one(
        'mrp.production',
        string='Production',
    )
    orders_ids = fields.Many2many(
        'sale.order',
        string='Sales Orders',
        readonly=True,
    )
    mass_orders_ids = fields.Many2many(
        'sale.order',
        'mass_sale_order_rel',
        string='Mass Orders',
    )
    move_id = fields.Many2one(
        'stock.move',
        string='Move',
        readonly=True,
    )
    component_lots_ids = fields.Many2many(
        related='move_id.lot_ids'
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        compute='_compute_product_id',
    )
    state = fields.Selection(
        [('initial', 'Initial'), ('finish', 'Finish')],
        default='initial',
        required=True,
        readonly=True,
    )

    @api.depends('lot_id')
    def _compute_allowed_production_ids(self):
        for wizard in self:
            mos = self.env['mrp.production'].search([('lot_producing_id', '=', wizard.lot_id.id)])
            wizard.allowed_production_ids = mos

    @api.depends('move_id', 'state', 'lot_id')
    def _compute_product_id(self):
        for wizard in self:
            if wizard.state == 'initial':
                wizard.product_id = wizard.lot_id.product_id
            else:
                wizard.product_id = wizard.move_id.product_id

    def action_confirm(self):
        self.ensure_one()
        recall = self.env['recall.recall'].sudo().create({
            'production_id': self.production_id.id,
            'recall_class': self.recall_class,
        })
        orders = self.production_id.mapped('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id')
        orders.write({
            'recall_id': recall.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'recall.recall',
            'views': [[self.env.ref('aznut_complaint_claim.recall_form').id, 'form']],
            'res_id': recall.id,
            'target': 'fullscreen',
        }

    def send_recall_mail_mass(self):
        self.ensure_one()
        send_recall_mail(self.mass_orders_ids)

    def send_recall_mail_all(self):
        self.ensure_one()
        send_recall_mail(self.orders_ids)
