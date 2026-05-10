from odoo import fields, models


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    actual_lead_time = fields.Integer(
        string='Actual Lead Time'
    )
    supplier_price = fields.Float(
        string='Supplier Price',
    )

    def _select(self):
        return super(PurchaseReport, self)._select() + """
            , MIN(vendor_info.actual_lead_time) AS actual_lead_time
            , MIN(vendor_info.price_unit) AS supplier_price
        """

    def _from(self):
        return super(PurchaseReport, self)._from() + """
            LEFT JOIN LATERAL (
                SELECT 
                    EXTRACT(EPOCH FROM (sp.date_done - po_new.create_date)) / 86400 AS actual_lead_time,
                    pol.price_unit
                FROM purchase_order_line pol
                INNER JOIN stock_move sm ON sm.purchase_line_id = pol.id
                INNER JOIN stock_picking sp ON sm.picking_id = sp.id
                INNER JOIN purchase_order po_new ON po_new.id = pol.order_id
                WHERE 
                    sp.state = 'done' 
                    AND pol.id = l.id
                ORDER BY sp.date_done DESC
                LIMIT 1
            ) AS vendor_info ON TRUE
        """
