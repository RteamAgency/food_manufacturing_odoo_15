from odoo import models, fields, api


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    allowed_lot_ids = fields.Many2many(
        'stock.production.lot',
        string='Lots',
        compute="_compute_allowed_lot_ids",
    )

    @api.depends('product_id', 'owner_id', 'package_id', 'location_id', 'scrap_qty')
    def _compute_allowed_lot_ids(self):
        for scrap in self:
            suitable_quants = self.env['stock.quant'].search([
                ('location_id', 'child_of', scrap.location_id.id),
                ('owner_id', '=', scrap.owner_id.id),
                ('package_id', '=', scrap.package_id.id),
                ('product_id', '=', scrap.product_id.id),
            ]).filtered(lambda quant: quant.available_quantity >= scrap.scrap_qty)
            scrap.allowed_lot_ids = suitable_quants.mapped('lot_id')

    @api.onchange('location_id', 'product_id', 'package_id', 'owner_id', 'scrap_qty')
    def _onchange_parameters(self):
        self.lot_id = False
