from odoo import api, SUPERUSER_ID

from odoo.addons.aznut_purchase.models.res_config_settings import VendorAvailabilityEmailText, \
    ShippingInformationRequestEmailText, ConfirmationToSupplierEmailText, RequestForVendorEmailText


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for order in env['purchase.order'].search([]):
        order.write({'access_token': order._default_access_token()})
    env['ir.config_parameter'].sudo().set_param(
        "aznut_purchase.vendor_availability_email_template", VendorAvailabilityEmailText
    )
    env['ir.config_parameter'].sudo().set_param(
        "aznut_purchase.shipping_information_request_email_template", ShippingInformationRequestEmailText
    )
    env['ir.config_parameter'].sudo().set_param(
        "aznut_purchase.confirmation_to_supplier_email_template", ConfirmationToSupplierEmailText
    )
    env['ir.config_parameter'].sudo().set_param(
        "aznut_purchase.request_for_vendor_email_template", RequestForVendorEmailText
    )

