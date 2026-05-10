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
    'name': "Sale customization",

    'summary': """
        Sale customization
    """,
    'description': """
        Sale customization
    """,

    'version': '15.0.0.16',
    'category': 'Sales/Sales',
    'author': "Smarttek Solutions and Services",
    'license': "AGPL-3",
    'website': "https://smartteksas.com",

    'depends': ['mrp', 'website_sale', 'sale_margin', 'crm', 'account_reports', 'project', 'hr', 'aznut_stock'],

    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'wizard/reserve_sale_order_wizard_views.xml',
        'wizard/add_brand_wizard_views.xml',
        'views/sale_order_views.xml',
        'views/product_template_views.xml',
        'views/mrp_workorder_views.xml',
        'views/stock_quant_views.xml',
        'views/test_database_views.xml',
        'views/crm_lead_quality_views.xml',
        'views/crm_lead_views.xml',
        'views/stock_picking_views.xml',
        'data/mail_templates.xml',
        'data/mail_template_data.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'aznut_sale/static/src/js/project_list.js', ]
    },
    'installable': True,
    'post_load': 'post_load_hook'
}
