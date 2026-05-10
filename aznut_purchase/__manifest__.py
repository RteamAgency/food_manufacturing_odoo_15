{
    'name': "Purchase Customization",

    'summary': """
        Purchase Customization
    """,
    'description': """
       Aznut Purchase Customization
    """,

    'version': '15.0.0.7',
    'category': 'Inventory/Purchase',
    'license': "AGPL-3",

    'depends': ['aznut_mrp', 'purchase_stock'],
    'external_dependencies': {
        'python': ['emoji'],
    },

    'data': [
        'security/purchase_security.xml',
        'security/ir.model.access.csv',
        'security/ir.model.access.xml',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'views/product_category_views.xml',
        'views/product_views.xml',
        'views/website_templates.xml',
        'views/purchase_order_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_quant_views.xml',
        'report/purchase_order_templates.xml',
        'report/report_stock_forecasted.xml',
        'report/purchase_report_views.xml',
        'views/res_config_settings.xml',
        'report/vendor_lead_time_report.xml',
        'views/res_partner_views.xml',
        'report/purhase_jars_brand_report.xml',
        'report/purchase_jars_components_report.xml',
        'wizard/request_for_vendor_wizard_views.xml',
        'wizard/purchase_accelerator_view.xml',
        'wizard/change_product_category_wizard.xml',
    ],
    'assets': {

        'web.assets_qweb': [
            'aznut_purchase/static/src/xml/**/*',
        ],
        'web.assets_backend': [
            'aznut_purchase/static/src/scss/purchase.scss',
            'aznut_purchase/static/src/js/purchase_dashboard.js',
            'aznut_purchase/static/src/js/list_renderer.js',
        ],
        'web.assets_common': [
            'aznut_purchase/static/src/js/request_for_vendor.js',
            'aznut_purchase/static/src/js/availability_confirmation.js',
        ],
    },
    'installable': True,
    'post_load': 'post_load_hook',
}
