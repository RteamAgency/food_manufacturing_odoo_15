from odoo import fields, models, api

from ..models.product_category import _get_date_ranges


class VendorLeadTimeReport(models.Model):
    _name = "vendor.lead.time.report"
    _description = "Vendor Lead Time Report"
    _auto = False

    product_id = fields.Many2one(
        'product.product',
        string='Product', 
        readonly=True
    )
    date = fields.Datetime(
        string="RFQ Date"
    )
    lead_time = fields.Integer(
        string="Vendor Lead Time"
    )
    actual_lead_time = fields.Integer(
        string="Actual Lead Time"
    )
    price = fields.Float(
        string="Price"
    )
    
    @property
    def _table_query(self):
        ''' Report needs to be dynamic to take into account multi-company selected + multi-currency rates '''
        return '%s' % (self._select())

    def _select(self):
        date_ranges = _get_date_ranges(3)
        vendor_id = self.env.context.get('report_partner_id')
        query = """
            SELECT
                ROW_NUMBER() OVER (ORDER BY pol.date_planned DESC) AS id,
                pp.id AS product_id,
                psi.delay AS lead_time,
                pol.date_planned AS date,
                pol.price_unit AS price,
                po.create_date,
                po.id AS purchase_id,
                sp.date_done,
                EXTRACT(EPOCH FROM (sp.date_done - po.create_date)) / 86400 AS actual_lead_time
            FROM purchase_order_line pol
            JOIN purchase_order po ON pol.order_id = po.id
            JOIN product_product pp ON pol.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN res_partner rp ON po.partner_id = rp.id
            LEFT JOIN product_supplierinfo psi ON
                psi.product_tmpl_id = pt.id AND
                psi.name = po.partner_id

            LEFT JOIN LATERAL (
                SELECT sp.date_done
                FROM stock_move sm
                JOIN stock_picking sp ON sm.picking_id = sp.id
                WHERE sm.purchase_line_id = pol.id
                AND sp.state = 'done'
                ORDER BY sp.date_done ASC
                LIMIT 1
            ) sp ON TRUE

            WHERE po.state NOT IN ('cancel')
            AND po.create_date BETWEEN '{date_start}' AND '{date_end}'
            AND po.partner_id = {vendor_id}
            AND sp.date_done IS NOT NULL
            ORDER BY pol.date_planned DESC
        """.format(
            date_start=date_ranges[-1][0],
            date_end=date_ranges[0][1],
            vendor_id=vendor_id,
        )
        return query

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'lead_time' not in fields:
            return super(VendorLeadTimeReport, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        res = super(VendorLeadTimeReport, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for group in res:
            if group.get('__domain'):
                po_lines = self.search(group['__domain'])
                lead_times = po_lines.mapped('lead_time')
                actual_lead_times = po_lines.mapped('actual_lead_time')
                group['lead_time'] = (sum(lead_times) / len(lead_times) if lead_times else 0.0)
                group['actual_lead_time'] = (sum(actual_lead_times) / len(actual_lead_times) if actual_lead_times else 0.0)
        return res
