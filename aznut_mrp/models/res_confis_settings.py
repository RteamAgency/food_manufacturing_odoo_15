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

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    label_per_quantity = fields.Integer(
        string='Label Per Quantity',
        config_parameter='aznut_mrp.label_per_quantity',
        default=100,
        required=True,
    )
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        domain=[('code', '=', 'internal')],
        config_parameter='aznut_mrp.picking_type_id',
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        config_parameter='aznut_mrp.location_id',
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        config_parameter='aznut_mrp.location_dest_id',
    )
    hide_total_margin = fields.Boolean(
        string='Hide Total Margin',
        config_parameter='aznut_mrp.hide_total_margin',
    )
