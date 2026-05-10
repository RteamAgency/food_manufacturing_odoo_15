from odoo import fields, models, api

VendorAvailabilityEmailText = """<p>Dear %name%,</p>
<p>Please click the link below to view the draft Purchase Order and the ingredients list.</p>
<p><a href="%link%" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: #ffffff; text-decoration: none; border-radius: 5px;">View Purchase Order</a></p>
<p>Kindly let us know which ingredients are currently in stock (including their ready-to-ship dates) and which are out of stock (along with their expected restock dates).</p>
<p>We greatly appreciate accurate and detailed information, as it helps us plan and scale our business efficiently. Thank you in advance.</p>
<p>Best regards,<br>BPWLAB Purchasing Department</p>"""

ShippingInformationRequestEmailText = """<p>Dear %name%,</p>
<p>We have received confirmation to pick up %order%.</p>
<p>Please provide the shipping information so we can schedule the pickup accordingly.</p>
<p>Once we receive the details, we will send you the BOL for the scheduled pickup.</p>
<p>Thank you.</p>
<p>Best regards,<br>BPWLAB Shipping Department</p>"""

ConfirmationToSupplierEmailText = """<p>Dear %name%,</p>
<p>Please find attached the Purchase Order, prepared based on the information you provided regarding ingredient availability.</p>
<p>The PO includes the scheduled pickup date. If you require a different pickup date, please let us know so we can make the necessary adjustments.</p>
<p>Thank you.</p>
<p>Best regards,<br>BPWLAB Purchasing Department</p>"""

RequestForVendorEmailText = """<p>Dear %name%,</p> <p>We are following up regarding several outstanding items 
from our recent orders. Below is a link to the summary of the unreceived products for which we would appreciate a status update, 
including available quantities and updated estimated time of arrival (ETA):</p> <a href="%link%" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: #ffffff; text-decoration: none; border-radius: 5px;">View Purchase Order</a>
<p>Please confirm the current 
availability and ETA for the outstanding items listed above at your earliest convenience.</p> <p>Thank you in advance 
for your cooperation and continued partnership.</p> <p>Best regards,<br> Underwriting</p>"""

email_fields = [
    'confirmation_to_supplier_email_template',
    'vendor_availability_email_template',
    'shipping_information_request_email_template',
    'request_for_vendor_email_template',
]


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    purchase_jars_forecast_ratio = fields.Float(
        string="Forecast Total Jars Ratio",
        config_parameter='aznut_purchase.jars_forecast_ratio',
        default=1.0,
    )
    total_jars_report_products = fields.Many2many(
        'product.product',
        string='Total Jars Components',
    )
    vendor_availability_email_template = fields.Char(
        string='Vendor Availability Email Template',
        config_parameter='aznut_purchase.vendor_availability_email_template',
    )
    shipping_information_request_email_template = fields.Char(
        string='Shipping Information Request Email Template',
        config_parameter='aznut_purchase.shipping_information_request_email_template',
    )
    confirmation_to_supplier_email_template = fields.Char(
        string='Confirmation To Supplier Email Template',
        config_parameter='aznut_purchase.confirmation_to_supplier_email_template',
    )
    request_for_vendor_email_template = fields.Char(
        string='Request for Vendor Email Template',
        config_parameter='aznut_purchase.request_for_vendor_email_template',
    )

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            "aznut_purchase.total_jars_report_products",
            ','.join(map(str, self.total_jars_report_products.ids))
        )
        for field in email_fields:
            if hasattr(self, field):
                self.env['ir.config_parameter'].sudo().set_param("aznut_purchase.%s" % field, getattr(self, field))

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        total_jars_report_products = params.get_param('aznut_purchase.total_jars_report_products', '')
        res.update(
            total_jars_report_products=[
                (6, 0, list(map(int, total_jars_report_products.split(','))))
            ] if total_jars_report_products else [(6, 0, [])]
        )
        return res
