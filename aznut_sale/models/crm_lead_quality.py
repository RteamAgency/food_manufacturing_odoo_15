from odoo import fields, models, api
from odoo.exceptions import ValidationError


class CrmLeadQuality(models.Model):
    _name = 'crm.lead.quality'
    _description = 'Crm Lead Quality'

    @api.constrains('due_value')
    def _check_due_value(self):
        for quality in self:
            if quality.due_value < 0:
                raise ValidationError('Due Value Must Be Positive!')

    name = fields.Char(
        string='Name',
        required=True,
    )
    description = fields.Text(
        string='Description',
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
    )
    due_type = fields.Selection(
        [('days', 'Days'),
         ('weeks', 'Weeks')],
        default='days',
        required=True,
    )
    due_value = fields.Integer(
        string='Due Value',
    )
    quality_type = fields.Selection(
        [('activity', 'Activity'), ('log_note', 'Log Note')],
        default='activity',
        required=True,
        string='Quality Type',
    )
    trigger_stage_id = fields.Many2one(
        'crm.stage',
        string='Trigger Stage',
        required=True,
    )
    sequence = fields.Integer(
        'Sequence',
        default=10,
    )
