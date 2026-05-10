from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    ready_quantity = fields.Float(
        string='Ready To Ship Quantity',
        compute='_compute_ready_quantity',
    )
    confirmed_by_client = fields.Boolean(
        string='Confirmed By Client',
        copy=False,
    )

    def _compute_ready_quantity(self):
        self.ready_quantity = False
        for picking in self.filtered(lambda pick: pick.state not in ['done', 'cancel']):
            ready_quantity = picking.sale_id.manufactured_qty - picking.sale_id.delivered_qty
            picking.ready_quantity = ready_quantity if ready_quantity > 0 else 0
