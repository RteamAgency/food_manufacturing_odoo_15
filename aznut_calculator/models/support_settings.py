from odoo import fields, models

ProcurementEmailText = """
<p>Dear %name%,</p>
<p>
Please check the list of ingredients requested by the customer, as they are currently not available in our inventory. 
Kindly advise if you have similar products in stock or if there's any possibility of sourcing them through our supply chain.
</p>
%ingredients%
<p>Best regards,</p> 
<p>Underwriting</p>
"""

ProcurementVendorsEmailText = """
<p>Dear %name%,</p>
<p>
Hello, this is the text.
</p>
%ingredients%
<p>Best regards,</p> 
<p>Underwriting</p>
"""

ManufacturingEmailText = """
<p>Dear %name%,</p>
<p>
We have a formula where the percentage of active ingredients is more than 30%. 
Please check the base and active ingredients ratio below and advise if we can offer this ratio to the customer.
</p>
%ingredients%
<p>Best regards,</p> 
<p>Underwriting</p>
"""

ApprovalEmailText = """
<p>Dear %name%,</p>
<p>We have a calculator for approving %calculator_name%.</p>
<p><a href="%link%" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: #ffffff; text-decoration: none; border-radius: 5px;">View Calculator</a></p>
<p>Best regards,</p> 
<p>Underwriting</p>
"""


class SupportSettings(models.Model):
    _name = 'support.settings'
    _description = 'Support Settings'

    gpt_text = fields.Text(
        string='Text',
    )
    gpt_token = fields.Char(
        string='Token',
    )
    name = fields.Char(
        string='Name',
        readonly=True,
    )
    procurement_text = fields.Html(
        string='Email Text',
        default=ProcurementEmailText,
    )
    procurement_vendors_text = fields.Html(
        string='Email Vendors Text',
        default=ProcurementVendorsEmailText,
    )
    procurement_partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
    )
    manufacturing_text = fields.Html(
        string='Email Text',
        default=ManufacturingEmailText,
    )
    manufacturing_partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
    )
    approval_partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
    )
    approval_text = fields.Html(
        string='Email Text',
        default=ApprovalEmailText,
    )
