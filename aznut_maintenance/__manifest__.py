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
    'name': "Maintenance customization",

    'summary': """
        Maintenance customization
    """,
    'description': """
        Maintenance customization
        15.0.0.0.2 - added possibility every day check, added Image functionality, 
        added ability to Generate PDF report - Print "Maintenance request report"
    """,

    'version': '15.0.0.0.2',
    'category': 'Manufacturing/Maintenance',

    'author': "Smarttek Solutions and Services",
    'license': "AGPL-3",
    'website': "https://smartteksas.com",

    'depends': ['mrp_maintenance'],

    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'wizard/maintenance_request_recurrence_wizard.xml',
        'views/maintenance_request_recurrence.xml',
        'views/maintenance_views.xml',
        'views/report_maintenance_request.xml',
        'views/maintenance_report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
