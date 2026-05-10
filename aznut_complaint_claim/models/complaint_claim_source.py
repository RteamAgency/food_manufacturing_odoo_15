from odoo import models, fields


class ComplaintClaimSource(models.Model):
    _name = 'complaint.claim.source'
    _description = 'Complaint Claim Source'

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', "Name must be unique."),
    ]

    name = fields.Char(
        string='Complaint Claim Source',
    )
