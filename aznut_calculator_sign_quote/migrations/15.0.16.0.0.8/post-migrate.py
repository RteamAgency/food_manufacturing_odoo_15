from odoo import api, SUPERUSER_ID

from json import loads
from os.path import join, dirname, abspath


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    path = join(dirname(abspath(__file__)), 'caclulators.json')
    with open(path, 'r') as j:
        contents = loads(j.read())
    for value in contents.values():
        child_calculator_vals = value.pop('custom_calculator_id')
        child_calculator_vals[0][2].update({'calculator_type': 'custom'})
        child_calculator = env['product.calculator'].create(child_calculator_vals[0][2])
        value.update(custom_calculator_id=child_calculator.id)
        if 'boms_to_map' in value:
            boms = value.pop('boms_to_map')
            env['mrp.bom'].browse(boms).write({'calculator_id': child_calculator.id})
        if value.get('signature'):
            value['signature'] = eval(value['signature']) if value['signature'] else False
        main_calculator = env['main.product.calculator'].create(value)
        main_calculator.calculator_ids = [(4, child_calculator.id)]
        main_calculator.active_calculator_id = child_calculator
        child_calculator.active_ingredient_ids.write({'calculator_id': child_calculator.id})
