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
    'name': "Stock Picking Customization",

    'summary': """
        Stock Picking Customization
    """,
    'description': """
        Stock Picking Customization
    """,
    'version': '15.0.0.9',
    'category': 'Inventory/Inventory',
    'author': "Smarttek Solutions and Services",
    'license': "AGPL-3",
    'website': "https://smartteksas.com",

    'depends': ['stock', 'quality_control', 'purchase_stock', 'product_expiry'],

    'data': [
        'data/mail_template_data.xml',
        'views/stock_picking_views.xml',
        'views/purchase_views.xml',
        'views/stock_product_lot_views.xml',
    ],
    'assets': {
        'web.assets_backend': {
            '/aznut_stock/static/src/js/kanban_tags_widget.js',
            '/aznut_stock/static/scss/kanban_tags_widget.scss',
        },
        'web.assets_qweb': {
            '/aznut_stock/static/src/xml/kanban_tags_widget.xml',
        },
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'post_load': 'post_load_hook',
}
