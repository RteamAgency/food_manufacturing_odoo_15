from odoo import fields, models, api
import datetime

class MailActivity(models.Model):
    _inherit = 'mail.activity'
     
    importance_level = fields.Selection([
        ('normal', 'Normal'),
        ('urgent', 'Urgent')],
        string="Importance level",
    )
    dashboard_attachment_ids = fields.Many2many(
        'ir.attachment', string="Attach File",
    )

    def action_schedule_dashboard_activity(self):
        return {'type': 'ir.actions.act_window_close'}
    
    @api.model
    def get_dashboard_activity_action(self):
        return {'action': {
            'view_id': self.env.ref('aznut_dashboard_ceo.mail_activity_view_form_popup_dashboard').id,
        }}

    def generate_urgent_activities_action(self):
        return {'action': {
            'view_id': self.env.ref('aznut_dashboard_ceo.mail_activity_view_tree_urgent').id,
            'domain': [('id', 'in', self.ids)],
        }}
    
    @api.onchange('user_id')
    def _onchange_user_id(self):
        if self.env.context.get('is_dashboard_action') and self.user_id:
            if self.user_id.employee_ids:
                self.res_id = self.user_id.employee_ids[0].id
                current_date = datetime.datetime.now()
                next_day =  (current_date + datetime.timedelta(days=1)).date()
                self.date_deadline = next_day

    def activity_format(self):
        result = super(MailActivity, self).activity_format()
        for activity in result:
            attach_ids = activity.get('dashboard_attachment_ids', False)
            if attach_ids:
                attachments = self.env['ir.attachment'].browse(attach_ids)
                if attachments:
                    activity.update({'dashboard_attachment_ids': attachments._attachment_format()})
        return result
