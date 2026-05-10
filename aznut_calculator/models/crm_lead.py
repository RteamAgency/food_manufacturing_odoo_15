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


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    main_product_calculator_id = fields.Many2one(
        'main.product.calculator',
        string='Chews Calculator',
    )
    main_powder_calculator_id = fields.Many2one(
        'main.powder.calculator',
        string='Powder Calculator',
    )
    show_sample_test_button = fields.Boolean(
        string='Show Sample Test Button',
        compute='_compute_bom_info',
    )
    allowed_boms_ids = fields.Many2many(
        string='Allowed Boms',
        compute='_compute_bom_info',
    )
    sample_test_orders_ids = fields.Many2many(
        'mrp.production',
        string='Sample Test Order',
    )
    product_calculators_count = fields.Integer(
        string='Product Calculator Count',
        compute='_compute_product_calculators_count',
    )
    powder_calculators_count = fields.Integer(
        string='Powder Calculator Count',
        compute='_compute_powder_calculators_count',
    )

    def _compute_product_calculators_count(self):
        for lead in self:
            lead.product_calculators_count = self.env['main.product.calculator'].search_count([
                ('lead_id', '=', lead.id)
            ])

    def _compute_powder_calculators_count(self):
        for lead in self:
            lead.powder_calculators_count = self.env['main.powder.calculator'].search_count([
                ('lead_id', '=', lead.id)
            ])

    def _compute_bom_info(self):
        BoM = self.env['mrp.bom']
        self.show_sample_test_button = self.allowed_boms_ids = False
        for lead in self:
            product_calculators = self.env['main.product.calculator'].search([('lead_id', '=', lead.id)])
            powder_calculators = self.env['main.powder.calculator'].search([('lead_id', '=', lead.id)])
            lead.allowed_boms_ids = BoM.search([
                '|',
                ('powder_calculator_id', 'in', powder_calculators.powder_calculator_ids.ids),
                ('product_calculator_id', 'in', product_calculators.calculator_ids.ids),
            ]).ids
            if lead.allowed_boms_ids:
                lead.show_sample_test_button = True

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.main_product_calculator_id.partner_id = self.partner_id
        self.main_powder_calculator_id.partner_id = self.partner_id

    def open_product_calculator(self):
        self.ensure_one()
        return {
            'name': 'Main Chews Calculators',
            'type': 'ir.actions.act_window',
            'res_model': 'main.product.calculator',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('aznut_calculator.main_product_calculator_tree_view').id, 'tree'),
                      (self.env.ref('aznut_calculator.main_product_calculator_form_view').id, 'form')],
            'target': 'current',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_partner_id': self.partner_id.id,
                        'default_lead_id': self.id},
        }

    def open_powder_calculator(self):
        self.ensure_one()
        return {
            'name': 'Main Powder Calculators',
            'type': 'ir.actions.act_window',
            'res_model': 'main.powder.calculator',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('aznut_calculator.main_powder_calculator_tree_view').id, 'tree'),
                      (self.env.ref('aznut_calculator.main_powder_calculator_form_view').id, 'form')],
            'target': 'current',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_partner_id': self.partner_id.id,
                        'default_lead_id': self.id},
        }

    def open_sample_test_order(self):
        return {
            'name': 'Sample Test Order',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],
            'target': 'current',
            'domain': [('id', 'in', self.sample_test_orders_ids.ids)],
            'context': {'create': False, }
        }

    def action_product_send_quote(self):
        self.ensure_one()
        res = self.main_product_calculator_id.send_by_email()
        return res

    def action_powder_send_quote(self):
        self.ensure_one()
        res = self.main_powder_calculator_id.send_by_email()
        return res

    def action_open_sample_test_wizard(self):
        self.ensure_one()
        return {
            'name': 'Sample Test',
            'type': 'ir.actions.act_window',
            'res_model': 'sample.test.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('aznut_calculator.sample_test_wizard_form').id,
            'target': 'new',
            'context': {
                'default_allowed_boms_ids': self.allowed_boms_ids.ids,
                'default_lead_id': self.id,
            }
        }

    def action_send_sample_test_report(self):
        self.ensure_one()
        orders = self.sample_test_orders_ids.filtered(lambda order: order.state == 'done')
        return {
            'name': 'Send Sample Test',
            'type': 'ir.actions.act_window',
            'res_model': 'send.sample.test.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('aznut_calculator.send_sample_test_wizard_form').id,
            'target': 'new',
            'context': {
                'default_allowed_sample_test_orders_ids': orders.ids,
                'default_partner_id': self.partner_id.id,
            }
        }
