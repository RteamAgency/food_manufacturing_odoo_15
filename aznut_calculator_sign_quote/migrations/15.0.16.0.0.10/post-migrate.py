from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    main_calculators = env['main.product.calculator'].search([('signature', '!=', False)])
    for main_calculator in main_calculators:
        main_calculator.write({'is_locked': True})
