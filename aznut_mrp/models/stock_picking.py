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

from odoo import models, fields


class StockPicking(models.Model):
    _inherit = "stock.picking"

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for picking in self.filtered(lambda pick: pick.state == 'done'):
            dest_pickings = picking.mapped('move_lines.move_dest_ids.picking_id')
            if dest_pickings:
                dest_pickings.action_assign()
        return res
