from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _get_allowed_menus(self):
        menues, restricted_menues = super(IrUiMenu, self)._get_allowed_menus()
        current_user = self.env.user
        if current_user.has_group('aznut_purchase.group_receiving_operator'):
            menues += [
                self.env.ref('aznut_purchase.menu_purchase_rfq_receiving_operator').id,
                self.env.ref('aznut_purchase.menu_purchase_form_action_receiving_operator').id,
                self.env.ref('aznut_purchase.menu_internal_pickings_receiving_operator').id,
                self.env.ref('aznut_purchase.menu_receipts_receiving_operator').id,
                self.env.ref('purchase.menu_purchase_root').id,
                self.env.ref('purchase.menu_procurement_management').id,
                self.env.ref('base.menu_administration').id,
                self.env.ref('base.menu_users').id,
                self.env.ref('base.menu_action_res_users').id,
                self.env.ref('base.menu_action_res_groups').id,
                self.env.ref('stock.menu_stock_root').id,
                self.env.ref('stock.stock_picking_type_menu').id,
                self.env.ref('stock.menu_stock_inventory_control').id,
                self.env.ref('stock.menu_product_variant_config_stock').id,
                self.env.ref('stock.product_product_menu').id,
                self.env.ref('stock.menu_package').id,
                self.env.ref('stock.menu_action_production_lot_form').id,
                self.env.ref('stock.menu_stock_warehouse_mgmt').id,
                self.env.ref('aznut_sale.menu_products_main').id,
                self.env.ref('aznut_sale.menu_product_template').id,
                self.env.ref('aznut_sale.menu_product_product').id,
            ]
        else:
            restricted_menues += [
                self.env.ref('aznut_purchase.menu_purchase_rfq_receiving_operator').id,
                self.env.ref('aznut_purchase.menu_purchase_form_action_receiving_operator').id,
                self.env.ref('aznut_purchase.menu_internal_pickings_receiving_operator').id,
                self.env.ref('aznut_purchase.menu_receipts_receiving_operator').id,
            ]
        return menues, restricted_menues
