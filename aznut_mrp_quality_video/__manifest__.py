{
    'name': "MRP Quality Video",

    'summary': """
        MRP Quality Video
    """,
    'description': """
        MRP Quality Video
    """,

    'version': '15.0.0.1',
    'category': 'Manufacturing/Manufacturing',

    'license': "AGPL-3",

    'depends': ['aznut_mrp'],

    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/mrp_quality_video_views.xml',
        'views/mrp_production_views.xml',
        'views/mrp_workorder_views.xml',
        'report/quality_alert_report_template.xml',
        'report/quality_alert_report.xml',
    ],
    'assets': {
        'web.assets_qweb': [
            'aznut_mrp_quality_video/static/src/xml/media_record_dialog/media_record_dialog.xml',
        ],
        'web.assets_backend': [
            'aznut_mrp_quality_video/static/src/js/media_record_dialog/media_record_dialog.js',
            'aznut_mrp_quality_video/static/src/js/mrp.js',
            'aznut_mrp_quality_video/static/src/lib/recordrtc/RecordRTC.js',
            'aznut_mrp_quality_video/static/src/scss/media_recorder_dialog.scss',
            'aznut_mrp_quality_video/static/src/scss/video_record_btn.scss',
            'aznut_mrp_quality_video/static/src/js/views/form_renderer.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
