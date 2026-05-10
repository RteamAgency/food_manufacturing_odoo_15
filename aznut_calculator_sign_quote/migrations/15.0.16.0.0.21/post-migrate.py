from odoo import api, SUPERUSER_ID

from json import loads
from os.path import join, dirname, abspath


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    product_calculators = env['main.product.calculator'].search([])
    powder_calculators = env['main.powder.calculator'].search([])
    customer_signed_product_calculators = product_calculators.filtered(lambda calc: calc.signature)
    customer_signed_powder_calculators = powder_calculators.filtered(lambda calc: calc.signature)
    seller_signed_powder_calculators = powder_calculators.filtered(lambda calc: calc.company_signature)
    seller_signed_product_calculators = product_calculators.filtered(lambda calc: calc.company_signature)
    seller_signed_product_calculators.write({'calculator_status': 'signed_by_seller'})
    seller_signed_powder_calculators.write({'calculator_status': 'signed_by_seller'})
    customer_signed_powder_calculators.write({'calculator_status': 'signed_by_customer'})
    customer_signed_product_calculators.write({'calculator_status': 'signed_by_customer'})
    (powder_calculators - (seller_signed_powder_calculators | customer_signed_powder_calculators)).write(
        {'calculator_status': 'new'})
    (product_calculators - (seller_signed_product_calculators | customer_signed_product_calculators)).write(
        {'calculator_status': 'new'})
