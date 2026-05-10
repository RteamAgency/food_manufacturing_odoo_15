from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    pickings = env['stock.picking'].search([
        ('state', 'not in', ['done', 'cancel', 'draft']),
        ('picking_type_id', '=', env.ref('stock.picking_type_out').id),
        ('check_ids', '=', False)
    ])
    pickings.move_lines._create_quality_checks()
