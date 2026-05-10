from odoo import fields, models, api


class DashboardMailActivity(models.Model):
    _name = "dashboard.mail.activity"
    _description = "Dashboard Mail Activity"
    _auto = False
    
    name = fields.Char(
        string='Document Name', 
    )
    mail_activity_type_id = fields.Many2one(
        'mail.activity.type',
        string="Activity Type",
    )
    note = fields.Html(
        string="Note"
    )
    feedback = fields.Text(
        string="Feedback"
    )
    date_due = fields.Date(
        string='Date Due',
    )
    state = fields.Selection([
        ('assigned', 'Assigned'),
        ('done', 'Done')],
        string="State"                         
    )

    @property
    def _table_query(self):
        ''' Report needs to be dynamic to take into account multi-company selected + multi-currency rates '''
        return '%s' % (self._select())
    
    def _select(self):
        query = """
            SELECT 
                ma.id AS id,
                ma.res_name AS name,
                ma.activity_type_id AS mail_activity_type_id,
                ma.note AS note,
                NULL AS feedback,
                ma.date_deadline AS date_due,
                'assigned' AS state
            FROM 
                mail_activity ma
            WHERE 
                ma.importance_level = 'urgent'

            UNION

            SELECT 
                msg.id + 1000000 AS id, -- смещение ID, чтобы не пересекались
                msg.record_name AS name,
                msg.mail_activity_type_id AS mail_activity_type_id,
                msg.activity_note AS note,
                msg.activity_feedback AS feedback,
                msg.date AS date_due,
                'done' AS state
            FROM 
                mail_message msg
            WHERE 
                msg.activity_importance_level = 'urgent'
        """
        return query

    @api.model
    def generate_urgent_activities_action(self):
        return {'action': {
            'view_id': self.env.ref('aznut_dashboard_ceo.dashboard_mail_activity_view_tree').id,
        }}
