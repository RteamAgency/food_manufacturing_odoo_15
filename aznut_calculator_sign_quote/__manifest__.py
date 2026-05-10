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
    'name': "Aznut Calculator Sign Quote",

    'summary': """
        Aznut Calculator Sign Quote
    """,
    'description': """
        Aznut Calculator Sign Quote
    """,

    'version': '16.0.0.21',
    'author': "Smarttek Solutions and Services",
    'license': "AGPL-3",
    'data': [
        'security/ir.model.access.xml',
        'security/ir.model.access.csv',
        'data/product_calculator_data.xml',
        'views/product_calculator_views.xml',
        'views/powder_calculator_views.xml',
        'views/product_calculator_settings_views.xml',
        'views/calculator_report_template.xml',
        'views/portal_templates.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            '/aznut_calculator_sign_quote/static/src/scss/portal_quote.scss',
        ],
        'web.assets_backend': [
            '/aznut_calculator_sign_quote/static/src/scss/calculator_settings_sign.scss',
            '/aznut_calculator_sign_quote/static/src/js/aznut_field_binary_signature.js',
        ],

    },
    'website': "https://smartteksas.com",
    'application': True,
    'depends': ['aznut_calculator', 'website_sale', 'aznut_sale'],
    'installable': True,
}
