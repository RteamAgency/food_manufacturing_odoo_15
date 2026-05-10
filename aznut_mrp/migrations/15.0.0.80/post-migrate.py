from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    boms = env['mrp.bom'].search([])
    for bom in boms:
        production_operation = bom.operation_ids.filtered(lambda op: op.workcenter_id.production_station)[:1]
        premix_operation = bom.operation_ids.filtered(lambda op: op.workcenter_id.premix_station)[:1]
        if premix_operation and production_operation:
            print_label_qp = premix_operation.quality_point_ids.filtered(lambda q: q.test_type == 'print_label')[:1]
            if not production_operation.quality_point_ids.filtered(lambda qp: qp.test_type == 'print_label'):
                print_label_qp.copy({'operation_id': production_operation.id})
