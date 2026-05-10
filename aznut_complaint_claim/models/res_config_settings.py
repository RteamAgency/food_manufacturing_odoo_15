from odoo import models, fields


class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    complaint_claim_qa_user_id = fields.Many2one(
        'res.users',
        string='Complaint Claim QA User',
        config_parameter='aznut_complaint_claim.complaint_claim_qa_user_id',
    )
    complaint_claim_accounting_user_id = fields.Many2one(
        'res.users',
        string='Complaint Claim Accounting User',
        config_parameter='aznut_complaint_claim.complaint_claim_accounting_user_id',
    )
    complaint_claim_manufactory_user_id = fields.Many2one(
        'res.users',
        string='Complaint Claim Manufactory User',
        config_parameter='aznut_complaint_claim.complaint_claim_manufactory_user_id',
    )
    complaint_claim_ceo_user_id = fields.Many2one(
        'res.users',
        string='Complaint Claim CEO User',
        config_parameter='aznut_complaint_claim.complaint_claim_ceo_user_id',
    )
