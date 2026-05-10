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

from odoo import models


class ProductCalculatorCreateBomWizard(models.TransientModel):
    _inherit = 'product.calculator.create.bom.wizard'

    def action_confirm(self):
        self.ensure_one()
        for wizard_calculator in self.suitable_wizard_calculators_ids:
            commission = wizard_calculator.calculator_id.commission
            if wizard_calculator.calculator_id.total_price:
                wizard_calculator.product_tmpl_id.write({
                    'list_price': wizard_calculator.calculator_id.total_price,
                    'sales_commission': commission,
                })
        return super(ProductCalculatorCreateBomWizard, self).action_confirm()


class PowderCalculatorCreateBomWizard(models.TransientModel):
    _inherit = 'powder.calculator.create.bom.wizard'

    def action_confirm(self):
        self.ensure_one()
        for wizard_calculator in self.suitable_wizard_calculators_ids:
            commission = wizard_calculator.calculator_id.commission
            if wizard_calculator.calculator_id.total_price:
                wizard_calculator.product_tmpl_id.write({
                    'list_price': wizard_calculator.calculator_id.total_price,
                    'sales_commission': commission,
                })
        return super(PowderCalculatorCreateBomWizard, self).action_confirm()
