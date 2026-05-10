################################################################################
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

from odoo import models, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    # def button_start(self):
    #     self.ensure_one()
    #     if any(not time.date_end for time in self.time_ids.filtered(lambda t: t.user_id.id == self.env.user.id)):
    #         return True
    #     # As button_start is automatically called in the new view
    #     if self.state in ('done', 'cancel'):
    #         return True
    #
    #     if self.product_tracking == 'serial':
    #         self.qty_producing = 1.0
    #     elif self.qty_producing == 0 and not self.production_id._get_sources():
    #         if 1 < self.product_id.batch < self.qty_remaining:
    #             self.qty_producing = self.product_id.batch
    #         else:
    #             self.qty_producing = self.qty_remaining
    #
    #     self.env['mrp.workcenter.productivity'].create(
    #         self._prepare_timeline_vals(self.duration, datetime.now())
    #     )
    #     if self.production_id.state != 'progress':
    #         self.production_id.write({
    #             'date_start': datetime.now(),
    #         })
    #     if self.state == 'progress':
    #         return True
    #     start_date = datetime.now()
    #     vals = {
    #         'state': 'progress',
    #         'date_start': start_date,
    #     }
    #     if not self.leave_id:
    #         leave = self.env['resource.calendar.leaves'].create({
    #             'name': self.display_name,
    #             'calendar_id': self.workcenter_id.resource_calendar_id.id,
    #             'date_from': start_date,
    #             'date_to': start_date + relativedelta(minutes=self.duration_expected),
    #             'resource_id': self.workcenter_id.resource_id.id,
    #             'time_type': 'other'
    #         })
    #         vals['leave_id'] = leave.id
    #         return self.write(vals)
    #     else:
    #         if not self.date_planned_start or self.date_planned_start > start_date:
    #             vals['date_planned_start'] = start_date
    #             vals['date_planned_finished'] = self._calculate_date_planned_finished(start_date)
    #         if self.date_planned_finished and self.date_planned_finished < start_date:
    #             vals['date_planned_finished'] = start_date
    #         return self.with_context(bypass_duration_calculation=True).write(vals)

    def _compute_working_users(self):
        super(MrpWorkorder, self.sudo())._compute_working_users()
