from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _get_allowed_menus(self):
        menues, restricted_menues = [], []
        current_user = self.env.user
        if current_user.has_group('aznut_mrp.group_workcenter_operator') and not current_user.has_group(
                'mrp.group_mrp_user'):
            menues += [
                self.env.ref('mrp.menu_mrp_root').id,
                self.env.ref('mrp_workorder.menu_mrp_dashboard').id,
                self.env.ref('mrp.menu_mrp_manufacturing').id,
                self.env.ref('mrp.menu_mrp_reporting').id,
                self.env.ref('mrp.menu_mrp_production_action').id,
                self.env.ref('mrp.menu_mrp_workorder_todo').id,
                self.env.ref('mrp.menu_mrp_scrap').id,
                self.env.ref('mrp.menu_mrp_work_order_report').id,
                self.env.ref('mrp.menu_mrp_production_report').id,
                self.env.ref('mrp.menu_mrp_workcenter_productivity_report').id,
                self.env.ref('mrp.menu_mrp_unbuild').id,
                self.env.ref('base.menu_administration').id,
                self.env.ref('base.menu_users').id,
                self.env.ref('base.menu_action_res_users').id,
                self.env.ref('base.menu_action_res_groups').id,
            ]
        return menues, restricted_menues

    @api.returns('self')
    def _filter_visible_menus(self):
        allowed_ids, restricted_ids = self._get_allowed_menus()
        visible_menus = super(IrUiMenu, self)._filter_visible_menus()
        if allowed_ids:
            visible_menus = visible_menus.filtered(lambda menu: menu.id in allowed_ids)
        if restricted_ids:
            visible_menus = visible_menus.filtered(lambda menu: menu.id not in restricted_ids)
        return visible_menus
