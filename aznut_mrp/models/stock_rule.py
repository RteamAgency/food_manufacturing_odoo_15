# -*- coding: utf-8 -*-

from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values,
                         bom):
        res = super(StockRule, self)._prepare_mo_vals(product_id, product_qty, product_uom, location_id, name, origin,
                                                      company_id, values, bom)
        if values.get('group_id') and product_id:
            tag_string = ''
            tag_ids = values['group_id'].sale_id.tag_ids
            if tag_ids:
                tag_string = '[%s]' % ', '.join([x.name for x in tag_ids])
            res['name'] = '%s:%s%s' % (values.get('group_id').sale_id.display_name, tag_string, product_id.display_name)
        return res
