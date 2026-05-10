from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    user_partner_id = fields.Many2one(
        'res.partner',
        related_sudo=True,
    )
