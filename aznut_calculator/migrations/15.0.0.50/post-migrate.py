from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    product_calculators = env['product.calculator'].search([])
    powder_calculators = env['powder.calculator'].search([])
    partner = env['res.users'].search([('name', '=', 'Marina')], limit=1).partner_id
    env.ref('aznut_calculator.support_settings_main').write({'approval_partner_id': partner.id})
    powder_calculators.write({'approval_partner_id': partner.id})
    product_calculators.write({'approval_partner_id': partner.id})

