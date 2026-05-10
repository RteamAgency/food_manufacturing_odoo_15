from odoo import models, fields

from ..wizard.recall_wizard import get_mail_compose_wizard


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    recall_id = fields.Many2one(
        'recall.recall',
        string='Recall',
    )
    recall_is_sent = fields.Boolean(
        string='Recall Is Sent',
    )

    def action_open_complaint_claim(self):
        return {
            'name': 'Complaint Claim',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'complaint.claim.wizard',
            'view_id': self.env.ref('aznut_complaint_claim.complaint_claim_wizard_form').id,
            'target': 'new',
            'context': {'default_order_id': self.id}
        }

    def send_recall_mail(self):
        self.ensure_one()
        return get_mail_compose_wizard(self)
