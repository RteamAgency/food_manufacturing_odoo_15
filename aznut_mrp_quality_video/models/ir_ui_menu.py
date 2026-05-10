from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def get_allowed_menus_for_workcenter_operator(self):
        res = super(IrUiMenu, self).get_allowed_menus_for_workcenter_operator()
        res.append(self.env.ref('aznut_mrp_quality_video.menu_mrp_quality_video_tree').id)
        return res
