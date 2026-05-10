# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class MrpReport(models.Model):
    _inherit = 'mrp.report'

    total_ordered = fields.Float(
        string='Total Ordered Qty',
        readonly=True,
        group_operator="sum",
    )
    total_margin = fields.Float(
        string='Total Margin',
        readonly=True,
        group_operator="sum",
    )
    margin_percent = fields.Float(
        string='Margin Percent',
        readonly=True,
        group_operator="avg",
    )

    def _select(self):
        return super(MrpReport, self)._select() + '''
            , COALESCE(SUM(total_ordered_distinct.total_ordered), 0.0) AS total_ordered
            , COALESCE(SUM(total_ordered_distinct.total_margin), 0.0) AS total_margin
            , COALESCE(AVG(total_ordered_distinct.margin_percent), 0.0) AS margin_percent
        '''

    def _from(self):
        new_request = '''
            LEFT JOIN (
                SELECT 
                    mo.id AS mo_id,
                    SUM(sol.price_subtotal) AS total_ordered,
                    SUM(sol.price_subtotal - (sol.purchase_price * sol.product_uom_qty)) AS total_margin,
                    CASE 
                        WHEN SUM(sol.price_subtotal) = 0 THEN 0
                        ELSE SUM(sol.price_subtotal - (sol.purchase_price * sol.product_uom_qty)) / SUM(sol.price_subtotal)
                    END AS margin_percent
                FROM mrp_production mo
                LEFT JOIN (
                    SELECT 
                        mo.id AS mo_id,
                        ARRAY_AGG(DISTINCT sol.id) AS so_ids
                    FROM mrp_production mo
                    LEFT JOIN stock_move sm ON sm.created_production_id = mo.id
                    LEFT JOIN procurement_group pg ON sm.group_id = pg.id
                    LEFT JOIN sale_order so ON so.id = pg.sale_id
                    LEFT JOIN sale_order_line sol ON sol.order_id = so.id
                    WHERE sol.product_id = mo.product_id
                    GROUP BY mo.id
                ) AS table_ordered ON table_ordered.mo_id = mo.id
                LEFT JOIN sale_order_line sol ON sol.id = ANY(table_ordered.so_ids)
                GROUP BY mo.id
            ) total_ordered_distinct ON total_ordered_distinct.mo_id = mo.id
        '''
        return super(MrpReport, self)._from() + new_request
