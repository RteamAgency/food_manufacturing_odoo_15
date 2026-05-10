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

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _search_is_calculator_procurement_partner(self, operator, value):
        if operator != '=':
            if operator == '!=' and isinstance(value, bool):
                value = not value
            else:
                raise NotImplementedError()
        if value:
            query = """
                SELECT procurement_partner_id
                FROM main_product_calculator
                WHERE procurement_partner_id IS NOT NULL
                
                UNION
                
                SELECT procurement_partner_id
                FROM main_powder_calculator
                WHERE procurement_partner_id IS NOT NULL;
            """
        else:
            query = """
                SELECT procurement_partner_id
                FROM main_product_calculator
                WHERE procurement_partner_id IS NULL
          
                UNION
                
                SELECT procurement_partner_id
                FROM main_powder_calculator
                WHERE procurement_partner_id IS NULL;
            """
        self._cr.execute(query)
        res = self._cr.fetchall()
        if not res:
            return [(0, '=', 1)]
        return [('id', 'in', [r[0] for r in res])]

    product_calculator_count = fields.Integer(
        string='Chews Calculator Count',
        compute='_compute_product_calculator_count',
    )
    powder_calculator_count = fields.Integer(
        string='Powder Calculator Count',
        compute='_compute_powder_calculator_count',
    )
    is_calculator_procurement_partner = fields.Boolean(
        string='Is Calculator Procurement Partner',
        compute='_compute_is_calculator_procurement_partner',
        search='_search_is_calculator_procurement_partner'
    )

    def _compute_product_calculator_count(self):
        for rec in self:
            rec.product_calculator_count = self.env['main.product.calculator'].search_count(
                [('partner_id', '=', rec.id)])

    def _compute_powder_calculator_count(self):
        for rec in self:
            rec.powder_calculator_count = self.env['main.powder.calculator'].search_count(
                [('partner_id', '=', rec.id)])

    def _compute_is_calculator_procurement_partner(self):
        for rec in self:
            rec.is_calculator_procurement_partner = bool(rec.powder_calculator_count + rec.product_calculator_count)

    def show_product_calculators(self):
        self.ensure_one()
        return {
            'name': 'Chews Calculators',
            'type': 'ir.actions.act_window',
            'res_model': 'main.product.calculator',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('aznut_calculator.main_product_calculator_tree_view').id, 'tree'),
                      (self.env.ref('aznut_calculator.main_product_calculator_form_view').id, 'form')],
            'target': 'current',
            'domain': [('partner_id', '=', self.id)],
            'context': {'create': 0},
        }

    def show_powder_calculators(self):
        self.ensure_one()
        return {
            'name': 'Powder Calculators',
            'type': 'ir.actions.act_window',
            'res_model': 'main.powder.calculator',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('aznut_calculator.main_powder_calculator_tree_view').id, 'tree'),
                      (self.env.ref('aznut_calculator.main_powder_calculator_form_view').id, 'form')],
            'target': 'current',
            'domain': [('partner_id', '=', self.id)],
            'context': {'create': 0},
        }
