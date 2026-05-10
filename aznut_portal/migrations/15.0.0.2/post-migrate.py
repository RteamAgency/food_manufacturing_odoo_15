from odoo import api, SUPERUSER_ID

menus_to_unlink = [
    'pricing',
    'about us',
    'courses',
    'contact us'
]


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    websites = env['website'].search([])
    for website in websites:
        website_menus = env['website.menu'].search([('website_id', '=', website.id)])
        suitable_menus = website_menus.filtered(lambda rec: rec.name.lower() in menus_to_unlink)
        suitable_menus.write({
            'parent_id': False,
        })
