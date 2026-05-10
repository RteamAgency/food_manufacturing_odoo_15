from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _get_allowed_menus(self):
        menues, restricted_menues = super(IrUiMenu, self)._get_allowed_menus()
        current_user = self.env.user
        if current_user.has_group('aznut_calculator.group_calculator_salesperson'):
            menues += [
                self.env.ref('aznut_calculator.menu_product_calculator_main').id,
                self.env.ref('aznut_calculator.menu_calculators').id,
                self.env.ref('aznut_calculator.menu_product_calculators').id,
                self.env.ref('aznut_calculator.menu_powder_calculator_tree').id,
                self.env.ref('base.menu_administration').id,
                self.env.ref('base.menu_users').id,
                self.env.ref('base.menu_action_res_users').id,
                self.env.ref('base.menu_action_res_groups').id,

            ]
        return menues, restricted_menues
