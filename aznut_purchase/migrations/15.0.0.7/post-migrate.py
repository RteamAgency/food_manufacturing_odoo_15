from odoo import api, SUPERUSER_ID

from odoo.addons.aznut_purchase.models.res_config_settings import RequestForVendorEmailText


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for order in env['purchase.order'].search([]):
        order.write({'request_for_vendor_access_token': order._default_access_token()})
    env['ir.config_parameter'].sudo().set_param(
        "aznut_purchase.request_for_vendor_email_template", RequestForVendorEmailText
    )
