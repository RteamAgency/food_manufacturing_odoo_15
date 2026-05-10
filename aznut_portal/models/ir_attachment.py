from odoo import models, fields


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    uploaded_from_portal = fields.Boolean(
        string='Uploaded From Portal',
    )
