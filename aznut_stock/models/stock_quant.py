from odoo import models
from datetime import datetime


class StockPicking(models.Model):
    _inherit = 'stock.quant'

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        res = super()._gather(product_id, location_id, lot_id, package_id, owner_id, strict)
        return res.sorted(
            key=lambda quant: (quant.lot_id.expiration_date or datetime.max, not quant.lot_id)
        )
