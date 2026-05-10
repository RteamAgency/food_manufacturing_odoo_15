from odoo import fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'
    
    activity_importance_level = fields.Selection([
        ('normal', 'Normal'),
        ('urgent', 'Urgent')],
        string="Activity Importance level",
    )
    activity_feedback = fields.Text(
        string="Feedback",
    )
    activity_note = fields.Html(
        string="Activity Note",
    )
