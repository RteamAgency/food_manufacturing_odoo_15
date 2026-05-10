from odoo import models

from collections import defaultdict


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _create_quality_checks_for_mo(self):
        mo_moves = defaultdict(lambda: self.env['stock.move'])
        check_vals_list = []
        for move in self:
            if move.production_id and not move.scrapped:
                mo_moves[move.production_id] |= move
        for production, moves in mo_moves.items():
            workcenters = production.mapped('workorder_ids.workcenter_id')
            if workcenters.filtered(lambda wk: wk.sample_test_station):
                continue
            quality_points = self._search_quality_points(moves.product_id, production.picking_type_id, 'operation')

            quality_points_lot_type = self._search_quality_points(production.product_id, production.picking_type_id,
                                                                  'product')
            quality_points = quality_points | quality_points_lot_type

            if not quality_points:
                continue
            mo_check_vals_list = quality_points._get_checks_values(moves.product_id, production.company_id.id,
                                                                   existing_checks=production.sudo().check_ids)
            for check_value in mo_check_vals_list:
                check_value.update({
                    'production_id': production.id,
                })
            check_vals_list += mo_check_vals_list
        self.env['quality.check'].sudo().create(check_vals_list)
