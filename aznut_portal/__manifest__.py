{
    'name': "Portal Customization",

    'summary': """
        Portal Customization
    """,
    'description': """
        Portal Customization
    """,
    'version': '15.0.0.2',
    'category': 'Website/Website',
    'license': "AGPL-3",

    'depends': ['aznut_mrp', 'sale_stock', 'quality_control_worksheet', 'website_sale', 'aznut_calculator_sign_quote',
                'sale_stock', 'crm_iap_mine'],

    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'data/crm_stage_data.xml',
        'views/sale_portal_templates.xml',
        'views/website_templates.xml',
        'views/product_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_type_views.xml',
        'views/stock_picking_views.xml',
        'views/res_users_views.xml',
        'views/crm_lead_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            ('before', 'website_sale/static/src/js/website_sale.js', 'aznut_portal/static/src/js/variant_mixin.js'),
        ],
        'web.assets_common': [
            'aznut_portal/static/src/js/portal.js'
        ],
        'web.assets_backend': [
            'aznut_portal/static/src/js/leads_kanban_follow_up.js'
        ],
        'web.assets_qweb': [
            'aznut_portal/static/src/xml/leads_kanban_follow_up_views.xml'
        ],
    },
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'auto_install': False,
    'application': True,
}
