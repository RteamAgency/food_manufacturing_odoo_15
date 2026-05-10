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
    'name': "MRP customization",

    'summary': """
        MRP customization
    """,
    'description': """
        MRP customization
        15.0.0.67 - added ability to create backorder
    """,

    'version': '15.0.0.82',
    'category': 'Manufacturing/Manufacturing',

    'author': "Smarttek Solutions and Services",
    'license': "AGPL-3",
    'website': "https://smartteksas.com",

    'depends': ['mrp', 'mrp_workorder', 'aznut_sale', 'quality_control', 'aznut_sale_margin', 'hr_attendance',
                'quality_control_worksheet', 'mrp_account_enterprise'],

    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/packaging_image_line.xml',
        'views/mrp_workorder_views.xml',
        'views/res_config_settings_views.xml',
        'views/mrp_workcenter_views.xml',
        'views/product_product_views.xml',
        'views/quality_check_premix_line_views.xml',
        'views/quality_point_views.xml',
        'views/quality_check_views.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_production_views.xml',
        'views/stock_picking_type_views.xml',
        'views/sale_order_views.xml',
        'views/stock_move_views.xml',
        'views/stock_scrap_views.xml',
        'views/mrp_report_pivot_views.xml',
        'views/res_users_views.xml',
        'report/mrp_report_bom_structure.xml',
        'report/mrp_production_templates.xml',
        'report/report_lot_barcode.xml',
        'report/report_containers_labels.xml',
        'report/mrp_production_cleaning_remplates.xml',
        'report/mrp_report_views.xml',
        'report/cost_structute_report.xml',
        'wizards/move_reserve_wizard_views.xml',
        'wizards/set_scheduled_date_wizard_views.xml',
        'wizards/upload_lot_image_wizard_views.xml',
        'wizards/put_container_number_wizard_views.xml',
        'wizards/confirm_production_quantity_wizard.xml',
        'wizards/number_packages_wizard_views.xml',
    ],
    'assets': {
        'web.assets_qweb': [
            'aznut_mrp/static/src/xml/deficit_widget.xml',
        ],
        'web.assets_backend': [
            '/aznut_mrp/static/src/scss/*.scss',
            'aznut_mrp/static/src/js/list_controller.js',
            'aznut_mrp/static/src/js/deficit_widget.js',
            'aznut_mrp/static/src/js/barcode_form_view.js',
            'aznut_mrp/static/src/js/list_renderer_agregates.js',
            'aznut_mrp/static/src/js/list_renderer.js',
            'aznut_mrp/static/src/js/kanban_column_progressbar.js',
            'aznut_mrp/static/src/js/gretting_message.js',
            'aznut_mrp/static/src/js/kanban_controller.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'post_load': 'post_load_hook',
}
