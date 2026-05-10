from odoo import models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        lot_id = self._context.get('lot_id', lot_id)
        location_id = self._context.get('location_id', location_id)
        owner_id = self._context.get('owner_id', owner_id)
        package_id = self._context.get('package_id', package_id)
        return super()._gather(product_id, location_id, lot_id, package_id, owner_id, strict)
