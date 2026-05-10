from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    calculators = env['product.calculator'].search([])
    main_calculators = env['main.product.calculator'].search([])
    setting_ingredients = env['product.calculator.settings'].search([]).mapped('base_ingredient_ids.id')
    env['base.ingredient'].search([('id', 'not in', setting_ingredients)]).unlink()
    env['active.ingredient'].search([]).unlink()
    calculators.unlink()
    main_calculators.unlink()
