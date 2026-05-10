###############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2019 SmartTek (<https://smartteksas.com/>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
################################################################################

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    total_sales_commission = fields.Float(
        'Total Sales Commission',
        readonly=True,
    )

    def _select_additional_fields(self, fields):
        fields['total_sales_commission'] = (
            ", CASE WHEN l.product_id IS NOT NULL THEN sum(CASE when l.sales_commission IS NOT NULL AND l.product_uom_qty IS NOT Null THEN (l.sales_commission * l.product_uom_qty) ELSE 0 END / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END AS total_sales_commission"
        )
        return super(SaleReport, self)._select_additional_fields(fields)
