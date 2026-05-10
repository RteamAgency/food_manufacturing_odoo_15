{
    'name': "Aznut Complaint Claim",

    'summary': """
        Aznut Complaint Claim
    """,
    'description': """
        Aznut Complaint Claim
    """,

    'version': '15.0.0.2',
    'category': 'Human Resources/Approvals',

    'license': "AGPL-3",

    'depends': ['sign', 'website_sale', 'mrp', 'product_expiry'],

    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'data/ir_sequence_data.xml',
        'wizard/complaint_claim_wizard_views.xml',
        'wizard/recall_wizard_views.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/complaint_claim_views.xml',
        'views/recall_views.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}
