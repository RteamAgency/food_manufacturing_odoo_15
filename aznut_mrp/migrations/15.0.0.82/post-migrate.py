import datetime
import pytz
import tzlocal
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    group = env['res.groups'].search([('name', 'ilike', 'Aznut Mrp Administrator')], limit=1)
    category = group.category_id
    group.unlink()
    category.unlink()
