from odoo import models, fields

from datetime import timedelta


def get_suitable_mo(mos, picking):
    def find_related_moves(start_moves, target_moves):
        related_moves = start_moves.filtered(lambda move: move in target_moves)
        to_check_moves = start_moves - related_moves

        while to_check_moves:
            next_moves = to_check_moves.mapped('move_dest_ids')
            matching_moves = next_moves.filtered(lambda move: move in target_moves)
            related_moves |= matching_moves
            to_check_moves = next_moves - matching_moves
        return True if related_moves else False

    return mos.filtered(lambda mrp_order: find_related_moves(mrp_order.move_dest_ids, picking.move_lines))[:1]


class StockPicking(models.Model):
    _inherit = "stock.picking"

    qa_status = fields.Selection(
        [('approved', 'QA Approved'),
         ('not_approved', 'Not Approved')],
        string='QA Status',
    )
    is_overdue = fields.Boolean(
        compute='_compute_is_overdue',
        string='Is Overdue',
    )
    is_order_released = fields.Boolean(
        string='Is Order Released',
        compute='_compute_is_order_released'
    )

    def _compute_is_overdue(self):
        self.is_overdue = False
        for picking in self.filtered(lambda pick: pick.sale_id and pick.picking_type_code == 'outgoing'):
            groups = self.env['procurement.group'].search([('sale_id', '=', picking.sale_id.id)])
            mos = (groups.mapped('stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids') |
                   groups.mapped('mrp_production_ids')).filtered(lambda mrp_order: mrp_order.state == 'done').sorted(
                'date_finished', reverse=True)
            mo = get_suitable_mo(mos, picking)
            if mo:
                date_finished_delta = mo.date_finished.date() + timedelta(days=30)
                if picking.date_done:
                    picking.is_overdue = date_finished_delta < picking.date_done.date()
                else:
                    picking.is_overdue = fields.Date.today() > date_finished_delta

    def _compute_is_order_released(self):
        self.is_order_released = False
        needed_pickings = self.filtered(lambda order: order.sale_id.payment_status == 'paid')
        needed_pickings.is_order_released = True
        (self - needed_pickings).is_order_released = False
