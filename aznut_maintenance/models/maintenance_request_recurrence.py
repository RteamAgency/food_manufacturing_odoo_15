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
from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MaintenanceRequestRecurrenceMixin(models.AbstractModel):
    _name = 'maintenance.request.recurrence.mixin'
    _description = 'Maintenance Request Recurrence Mixin'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
    )
    repeat_day = fields.Selection(
        [('monday', 'Monday'),
         ('tuesday', 'Tuesday'),
         ('wednesday', 'Wednesday'),
         ('thursday', 'Thursday'),
         ('friday', 'Friday')],
        required=True,
        default='monday',
        string='Week Day',
    )
    repeat_number = fields.Integer(
        string='Repeat Interval',
        default=1,
    )
    repeat_period = fields.Selection(
        selection=[
            ('day', 'Day'),
            ('week', 'Week'),
        ],
        default='week',
        required=True,
        string='Repeat Period',
    )
    maintenance_request_id = fields.Many2one(
        'maintenance.request',
        required=True,
    )
    next_date = fields.Date(
        string='Next Date',
        required=True,
    )

    @api.constrains('repeat_number')
    def _constrains_repeat_number(self):
        for record in self:
            if record.repeat_number <= 0:
                raise ValidationError(_('Invalid repeat number!'))

    @api.constrains('next_date', 'repeat_day')
    def _constrains_next_date(self):
        for record in self:
            if record.next_date <= fields.Date.today():
                raise ValidationError(_('You cannot use past dates or today"s date!'))
            elif record.next_date.strftime("%A").lower() != record.repeat_day.lower():
                raise ValidationError(_('Not valid week day! Need to be %s!' % record.repeat_day.capitalize()))

    @api.depends('repeat_number', 'maintenance_request_id', 'repeat_period', 'repeat_day')
    def _compute_name(self):
        name_fields = ['maintenance_request_id', 'repeat_number', 'repeat_period', 'repeat_day']
        for record in self:
            name = 'Recurrence:'
            for field in name_fields:
                if field == 'maintenance_request_id' and record.maintenance_request_id.name:
                    name = name + ' %s' % record.maintenance_request_id.name
                elif field == 'repeat_day' and record.repeat_day:
                    name = name + ' (%s)' % record.repeat_day.capitalize()
                elif field == 'repeat_number' and record.repeat_number > 0:
                    name = name + ' every %s' % record.repeat_number
                elif field == 'repeat_period' and record.repeat_period:
                    name = name + ' %s' % record.repeat_period
            record.name = name


class MaintenanceRequestRecurrence(models.Model):
    _name = 'maintenance.request.recurrence'
    _description = 'Maintenance Request Recurrence'
    _inherit = ['maintenance.request.recurrence.mixin']

    active = fields.Boolean(
        string='Active',
        default=True,
    )
    created_maintenance_requests_ids = fields.Many2many(
        'maintenance.request',
        string='Created Maintenance Requests',
    )

    def action_open_created_maintenance_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ruequests'),
            'view_mode': 'tree,form',
            'res_model': 'maintenance.request',
            'domain': [('id', '=', self.created_maintenance_requests_ids.ids)],
            'views': [[False, 'tree'], [False, 'form']],
            'target': 'current',
            'context': {'create': False}
        }

    def _cron_create_maintenance_request(self):
        records = self.env['maintenance.request.recurrence'].search([('active', '=', True)])
        for recurrence in records:
            today_dt = fields.Date.today()
            strt_wk_dt = today_dt - timedelta(days=today_dt.weekday())
            nd_wk_dt = strt_wk_dt + timedelta(days=6)
            nxt_strt_wk_dt = strt_wk_dt + timedelta(days=7)
            nxt_nd_wk_dt = nd_wk_dt + timedelta(days=7)
            if strt_wk_dt <= recurrence.next_date <= nd_wk_dt or nxt_strt_wk_dt <= recurrence.next_date <= nxt_nd_wk_dt:
                new_maintenance_request = recurrence.maintenance_request_id.copy({
                    'name': '%s %s' % (recurrence.maintenance_request_id.name, recurrence.next_date),
                    'request_date': today_dt,
                    'schedule_date': recurrence.next_date,
                })
                if recurrence.repeat_period == 'day':
                    next_date = recurrence.next_date + timedelta(days=recurrence.repeat_number)
                elif recurrence.repeat_period == 'week':
                    next_date = recurrence.next_date + timedelta(weeks=recurrence.repeat_number)
                else:
                    raise ValidationError(_('Invalid repeat period!'))
                recurrence.write({
                    'created_maintenance_requests_ids': [(4, new_maintenance_request.id)],
                    'next_date': next_date,
                })
