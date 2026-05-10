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

from odoo import models, _


class MaintenanceRequestRecurrenceWizard(models.TransientModel):
    _name = 'maintenance.request.recurrence.wizard'
    _description = 'Maintenance Request Recurrence Wizard'
    _inherit = ['maintenance.request.recurrence.mixin']

    def action_validate(self):
        self.ensure_one()
        recurrence = self.env['maintenance.request.recurrence'].create({
            'repeat_day': self.repeat_day,
            'repeat_number': self.repeat_number,
            'next_date': self.next_date,
            'name': self.name,
            'repeat_period': self.repeat_period,
            'maintenance_request_id': self.maintenance_request_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Recurrence'),
            'view_mode': 'form',
            'res_model': 'maintenance.request.recurrence',
            'res_id': recurrence.id,
            'view_id': self.env.ref('aznut_maintenance.maintenance_request_recurrence_form').id,
            'target': 'current',
            'context': {'create': False}
        }
