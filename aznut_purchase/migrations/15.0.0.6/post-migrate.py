from odoo import api, SUPERUSER_ID, fields


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['lead.time.history.line'].search([]).unlink()
    for seller_line in env['product.supplierinfo'].search([]):
        if seller_line.delay:
            seller_line.write({'lead_time_history_line_ids': [(0, 0, {
                'old_delay': 0,
                'new_delay': seller_line.delay,
                'date': fields.Datetime.now(),
                'partner_id': seller_line.name.id,
            })]})
