################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2019 SmartTek (<https://smartteksas.com/>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
################################################################################

{
    'name': "Aznut Calculator",

    'summary': """
        Aznut Calculator
    """,
    'description': """
        Aznut Calculator
    """,

    'version': '15.0.0.50',
    'author': "Smarttek Solutions and Services",
    'license': "AGPL-3",
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'data/product_calculator_data.xml',
        'data/mrp_production_data.xml',
        'report/calculator_report.xml',
        'report/calculator_main_report.xml',
        'data/mail_template_data.xml',
        'views/product_calculator_views.xml',
        'views/product_calculator_settings_views.xml',
        'views/crm_lead.xml',
        'views/res_partner_views.xml',
        'views/product_template_views.xml',
        'views/powder_calculator_views.xml',
        'views/ask_gpt_session_views.xml',
        'views/support_settings_views.xml',
        'views/mrp_views.xml',
        'wizard/product_calculator_create_bom_wizard_views.xml',
        'wizard/copy_product_calculator_wizard_views.xml',
        'wizard/compare_calculator_wizard_views.xml',
        'wizard/sample_test_wizard_views.xml',
        'wizard/send_sample_test_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/aznut_calculator/static/src/scss/calculator.scss',
            '/aznut_calculator/static/src/scss/chat.scss',
            '/aznut_calculator/static/src/js/list_renderer_agregates.js',
        ],
        'web.report_assets_pdf': [
            '/aznut_calculator/static/src/scss/calculator_report.scss',

        ],
        'web.report_assets_common': [
            '/aznut_calculator/static/src/scss/calculator_report.scss',
        ],
    },
    'website': "https://smartteksas.com",
    'application': True,
    'depends': ['base', 'uom', 'product', 'mail', 'aznut_mrp', 'sale_project', 'quality_mrp'],
    'external_dependencies': {
        'python': ['openai', 'emoji'],
    },
    'installable': True,
}
