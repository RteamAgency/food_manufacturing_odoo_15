from odoo import models, fields


class ProductCalculatorSettingsSign(models.Model):
    _name = 'product.calculator.settings.sign'
    _description = 'Product Calculator Settings Sign'

    name = fields.Char(
        string='Name',
        required=True,
    )
    company_signature = fields.Binary(
        string="Digital Signature"
    )


class ProductCalculatorSettings(models.Model):
    _inherit = 'product.calculator.settings'

    commission = fields.Float(
        string='Commission',
        digits=(16, 2),
    )
