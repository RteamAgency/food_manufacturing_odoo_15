from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    recalls = env['recall.recall'].search([])
    for recall in recalls:
        orders = recall.production_id.mapped('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id')
        orders.write({
            'recall_id': recall.id,
        })
