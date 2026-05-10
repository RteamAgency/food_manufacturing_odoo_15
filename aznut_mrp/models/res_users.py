from odoo import models, fields


class Users(models.Model):
    _inherit = "res.users"

    night_shift_user = fields.Boolean(
        string="Night Shift User",
    )
