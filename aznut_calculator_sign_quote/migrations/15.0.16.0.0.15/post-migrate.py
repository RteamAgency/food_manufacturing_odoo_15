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

from odoo import api, SUPERUSER_ID

from json import loads
from os.path import join, dirname, abspath


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    path = join(dirname(abspath(__file__)), 'caclulators.json')
    with open(path, 'r') as j:
        contents = loads(j.read())
    for key, value in contents.items():
        calculator = env['product.calculator'].browse(int(key))
        if calculator.exists():
            calculator.discount_amount = value
