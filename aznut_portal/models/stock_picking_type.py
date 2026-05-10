from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    count_picking_confirmed_by_client = fields.Integer(
        string='Count Picking Confirmed by Client',
        compute='_compute_count_picking_confirmed_by_client'
    )

    def _compute_count_picking_confirmed_by_client(self):
        self.count_picking_confirmed_by_client = False
        for picking_type in self.filtered(lambda tp: tp.code == 'outgoing'):
            count = self.env['stock.picking'].search_count([
                ('confirmed_by_client', '=', True),
                ('picking_type_id', '=', picking_type.id),
                ('state', '=', 'assigned'),
            ])
            picking_type.count_picking_confirmed_by_client = count

    def get_action_confirmed_by_client_shipping(self):
        action = self._get_action('stock.action_picking_tree_ready')
        action['context'].update({
            'search_default_confirmed_by_client': 1,
        })
        return action
