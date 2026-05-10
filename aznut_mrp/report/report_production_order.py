from odoo import models, api
from odoo.exceptions import ValidationError


class ProductionOrderReport(models.AbstractModel):
    _name = 'report.aznut_mrp.aznut_report_mrporder_inherited'
    _description = 'Production Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['mrp.production'].browse(docids)
        for doc in docs:
            is_cleaning = any(
                wo.workcenter_id.production_area_cleaning_station or 
                wo.workcenter_id.packaging_area_cleaning_station
                for wo in doc.workorder_ids)
            if is_cleaning:
                raise ValidationError("Unable to print Production Order for cleaning product")
            if doc.state != 'done':
                raise ValidationError("Unable to print report for manufacturing orders that are not in 'Done' status")
        return {
            'doc_ids': docs.ids,
            'doc_model': 'sale.order',
            'docs': docs,
        }
