from odoo import api, SUPERUSER_ID

from . import models
from . import controllers


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('website_sale.product_template_public').unlink()
    env['ir.module.module'].search([('name', '=', 'website_sale')]).write({"state": "to upgrade"})
