from odoo import fields, models, api

from ..models.product_category import _get_date_ranges


class PurchaseJarsComponentsReport(models.Model):
    _name = "purchase.jars.components.report"
    _description = "Purchase Jars Components Report"
    _auto = False

    component_id = fields.Many2one(
        'product.product',
        string='Component', 
        readonly=True
    )
    avg_component_qty_per_month = fields.Float(
        string="Average 3 month Qty"
    )
    avg_component_price = fields.Float(
        string="Average 3 month Cost"
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit',
        related='component_id.uom_id',
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
        multiplier_sql = f'* {next_month_ratio}' if self.env.context.get('for_next_month_component', False) else ''
        query = """            
            WITH cost_lines_agg AS (
                SELECT
                    product_id,
                    AVG(value_float) AS avg_price
                FROM (
                    SELECT
                        pchl.product_id,
                        irp.value_float,
                        pchl.date
                    FROM product_cost_history_line pchl
                    JOIN ir_property irp
                        ON irp.name = 'new_standard_price'
                        AND irp.res_id = CONCAT('product.cost.history.line,', pchl.id)
                    WHERE pchl.date BETWEEN '{date_start}' AND '{date_end}'
                ) sub
                WHERE value_float > 0
                GROUP BY product_id
            ),
            standard_prices_agg AS (
                SELECT
                    pp.id AS product_id,
                    AVG(irp.value_float) AS avg_price
                FROM product_product pp
                JOIN ir_property irp
                    ON irp.name = 'standard_price'
                    AND irp.res_id = CONCAT('product.product,', pp.id)
                GROUP BY pp.id
            ),
            sml_filtered AS (
                SELECT
                    sml.product_id,
                    SUM(sml.qty_done) AS qty_done_sum
                FROM stock_move_line sml
                JOIN stock_location loc ON sml.location_dest_id = loc.id
                WHERE sml.state = 'done'
                AND sml.date >= '{date_start}'
                AND sml.date <= '{date_end}'
                AND loc.name ILIKE '%%Production%%'
                AND sml.qty_done > 0
                GROUP BY sml.product_id
            )

            SELECT
                row_number() OVER (ORDER BY sml_filtered.product_id) AS id,
                sml_filtered.product_id AS component_id,
                sml_filtered.qty_done_sum / 3 {multiplier_sql} AS avg_component_qty_per_month,
                COALESCE(
                    cost_lines_agg.avg_price,
                    standard_prices_agg.avg_price
                ) AS avg_component_price
            FROM sml_filtered
            JOIN product_product pp ON sml_filtered.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN product_category pc ON pt.categ_id = pc.id
            LEFT JOIN cost_lines_agg ON cost_lines_agg.product_id = sml_filtered.product_id
            LEFT JOIN standard_prices_agg ON standard_prices_agg.product_id = sml_filtered.product_id
            WHERE sml_filtered.product_id IN ({components})
            GROUP BY sml_filtered.product_id, sml_filtered.qty_done_sum, cost_lines_agg.avg_price, standard_prices_agg.avg_price
            ORDER BY sml_filtered.product_id
        """.format(
            date_start=date_ranges[-1][0],
            date_end=date_ranges[0][1],
            components=components_sql,
            multiplier_sql=multiplier_sql
        )
        return query
    
    @api.model
    def get_report_action(self):
        params = self.env['ir.config_parameter'].sudo()
        components_raw = params.get_param('aznut_purchase.total_jars_report_products', '')
        next_month_ratio = float(self.env['ir.config_parameter'].sudo().get_param('aznut_purchase.jars_forecast_ratio'))
        components_list = list(map(int, components_raw.split(','))) if components_raw else []
        if not components_list:
            return False
        else:
            return {
                'name': 'Average Forecast Production of 3 month by Components',
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.jars.components.report',
                'view_mode': 'list',
                'views': [
                    (self.env.ref('aznut_purchase.view_purchase_jars_components_report_tree').id, 'list')
                ],
                'target': 'current',
            }
