################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2023 SmartTek (<https://smartteksas.com>).
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

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from num2words import num2words


class NumberPackagesWizard(models.TransientModel):
    _name = 'number.packages.wizard'
    _description = 'Number Packages Wizard'

    @api.constrains('number_of_packages')
    def _check_number_of_packages(self):
        for wizard in self:
            if wizard.number_of_packages <= 0:
                raise ValidationError(_('Number of packages cannot be less than or equal to zero'))

    number_of_packages = fields.Integer(
        string='Number of Packages',
    )
    production_id = fields.Many2one(
        'mrp.production',
        string='Workorder',
    )

    def action_confirm(self):
        self.ensure_one()
        lines_ids = []
        for number in range(self.number_of_packages):
            line = self.env['package.line'].create({
                'name': '%s Container' % num2words(number + 1, to='ordinal').capitalize()
            })
            lines_ids.append(line.id)
        packaging_wo = self.production_id.workorder_ids.filtered(lambda wo: wo.workcenter_id.packaging_station)[:1]
        packaging_wo.write({'package_lines_ids': lines_ids})
