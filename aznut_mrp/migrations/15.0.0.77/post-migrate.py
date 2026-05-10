from odoo import api, SUPERUSER_ID
from odoo.addons.aznut_mrp.wizards.put_container_number_wizard import generate_barcode_code

from num2words import num2words


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['package.line'].search([]).unlink()
    lines = env['quality.check.premix.line'].search([
        ('container_number', '>', '0')
    ])
    for line in lines.filtered(lambda l: l.quality_check_id.production_id.state not in ['done', 'cancel']):
        container_number = line.container_number
        production = line.quality_check_id.production_id
        if production:
            existing_package_line = production.package_lines_ids.filtered(lambda l: l.number == container_number)
            if not existing_package_line:
                existing_package_line = env['package.line'].create({
                    'name': '%s Container' % num2words(container_number, to='ordinal').capitalize(),
                    'number': container_number,
                    'barcode': generate_barcode_code(),
                })
                production.package_lines_ids |= existing_package_line
            line.write({'package_line_id': existing_package_line.id})
    env['mrp.production'].search([
        ('state', 'not in', ['done', 'cancel', 'draft'])
    ])._prepare_packaging()
