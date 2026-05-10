from odoo import fields, models, api

from ..models.product_category import _get_date_ranges


class PurchaseJarsBrandReport(models.Model):
    _name = "purchase.jars.brand.report"
    _description = "Purchase Jars Brand Report"
    _auto = False

    brand_name = fields.Char(
        string='Brand', 
        readonly=True
    )
    product_id = fields.Many2one(
        'product.product',
        string="Product",
    )
    avg_qty_produced_per_month = fields.Float(
        string="Average 3 month Qty"
    )
    avg_unit_price = fields.Float(
        string="Average 3 month Price"
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit',
    )
    total_percent = fields.Float(
        string="Total %",
        digits=(16, 4),
    )
    
    @property
    def _table_query(self):
        ''' Report needs to be dynamic to take into account multi-company selected + multi-currency rates '''
        return '%s' % (self._select())

    def _select(self):
        params = self.env['ir.config_parameter'].sudo()
        components_raw = params.get_param('aznut_purchase.total_jars_report_products', '')
        next_month_ratio = float(self.env['ir.config_parameter'].sudo().get_param('aznut_purchase.jars_forecast_ratio'))
        components_list = list(map(int, components_raw.split(','))) if components_raw else []
        components_sql = ','.join(str(id) for id in components_list)
        date_ranges = _get_date_ranges(3)
        multiplier_sql = f'* {next_month_ratio}' if self.env.context.get('for_next_month_brand', False) else ''
        query = """
            WITH qty_per_product AS (
                SELECT
                    MIN(mp.id) AS id,
                    p.id AS product_id,
                    pt.name AS product_name,
                    p.default_code,
                    COALESCE(pav.name, 'Undefined') AS brand_name,
                    SUM(sml.qty_done) AS total_qty,
                    pt.uom_id
                FROM mrp_production mp
                JOIN stock_move sm ON sm.production_id = mp.id AND sm.state != 'cancel'
                JOIN stock_move_line sml ON sml.move_id = sm.id
                JOIN product_product p ON mp.product_id = p.id
                JOIN product_template pt ON p.product_tmpl_id = pt.id
                JOIN product_category pc ON pt.categ_id = pc.id
                LEFT JOIN product_template_attribute_value ptav ON ptav.product_tmpl_id = pt.id
                LEFT JOIN product_attribute pa ON ptav.attribute_id = pa.id AND pa.name = 'Brand'
                LEFT JOIN product_attribute_value pav ON ptav.product_attribute_value_id = pav.id
                WHERE mp.state = 'done'
                AND mp.date_finished BETWEEN '{date_start}' AND '{date_end}'
                AND pc.name ILIKE '%%Dog Treats%%'
                AND sm.product_id = mp.product_id
                GROUP BY p.id, pt.name, p.default_code, COALESCE(pav.name, 'Undefined'), pt.uom_id
            )

            SELECT
                MIN(qpp.id) AS id,
                qpp.product_id,
                qpp.product_name,
                qpp.default_code,
                qpp.brand_name,
                qpp.uom_id,
                AVG(sol.price_unit) AS avg_unit_price,
                qpp.total_qty / 3 {multiplier_sql} AS avg_qty_produced_per_month,
                ROUND(qpp.total_qty / SUM(qpp.total_qty) OVER (), 4) AS total_percent
            FROM qty_per_product qpp
            LEFT JOIN sale_order_line sol ON sol.product_id = qpp.product_id
            LEFT JOIN sale_order so ON so.id = sol.order_id
            GROUP BY qpp.product_id, qpp.product_name, qpp.default_code, qpp.brand_name, qpp.total_qty, qpp.uom_id
            ORDER BY qpp.brand_name, qpp.product_name
        """.format(
            date_start=date_ranges[-1][0],
            date_end=date_ranges[0][1],
            components=components_sql,
            multiplier_sql=multiplier_sql
        )
        return query
    
    @api.model
    def get_report_action(self):
        return {
            'name': 'Average Forecast Production of 3 month by Brands',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.jars.brand.report',
            'view_mode': 'list',
            'views': [
                (self.env.ref('aznut_purchase.view_purchase_jars_brand_report_tree').id, 'list')
            ],
            'target': 'current',
            'context': {
                'group_by': 'brand_name'
            }
        }
