from odoo import models, fields

from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _inherit = 'stock.move'

    sale_orders_ids = fields.Many2many(
        'sale.order',
        'sale_order_rel',
        compute='_compute_sale_orders_ids',
    )

    recall_made = fields.Boolean(
        string='Recall Made',
        compute='_compute_recall_made',
    )

    def _compute_sale_orders_ids(self):
        self.sale_orders_ids = False
        for move in self:
            lots = move.mapped('move_line_ids.lot_id')
            if lots:
                domain = [('lot_id', 'in', lots.ids)]
            else:
                domain = [('product_id', '=', move.product_id.id)]

            move_lines = self.env['stock.move.line'].search(domain)
            mos = move_lines.mapped('move_id.raw_material_production_id')
            orders = mos.mapped('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id')
            move.sale_orders_ids = orders

    def _compute_recall_made(self):
        self.recall_made = False
        for move in self:
            move.recall_made = bool(move.sale_orders_ids.filtered(lambda so: so.recall_is_sent))

    def action_recall(self):
        self.ensure_one()

        if not self.sale_orders_ids:
            raise ValidationError('No orders found!')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Component Recall',
            'view_mode': 'form',
            'res_model': 'recall.wizard',
            'target': 'new',
            'view_id': self.env.ref('aznut_complaint_claim.recall_wizard_form').id,
            'context': {
                'default_orders_ids': self.sale_orders_ids.ids,
                'default_move_id': self.id,
                'default_state': 'finish',

            }
        }
