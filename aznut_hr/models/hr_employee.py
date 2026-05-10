from odoo import fields, models


class HrEmployee(models.AbstractModel):
    _inherit = 'hr.employee.base'

    current_workorders = fields.Html(
        'mrp.workorder',
        compute='_compute_current_workorders',
    )

    def _compute_current_workorders(self):
        for employee in self:
            wo_labels = self.sudo().env['mrp.workorder'].find_workorders_by_employee(employee.id)
            if wo_labels:
                workorder_list = ['<li class="o_force_ltr" style="color:green;">%s</li>' % label['header'] for label in
                                  wo_labels]
                employee.current_workorders = '<li><b>Current Operation:</b></li>' + ''.join(workorder_list)
            else:
                employee.current_workorders = False
