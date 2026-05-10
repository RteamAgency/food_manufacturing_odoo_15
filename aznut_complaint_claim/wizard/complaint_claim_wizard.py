from odoo import fields, models
from odoo.exceptions import ValidationError

from werkzeug.urls import url_join

USERS = [
    'complaint_claim_qa_user_id',
    'complaint_claim_accounting_user_id',
    'complaint_claim_ceo_user_id'
]


class ComplaintClaimWizard(models.Model):
    _name = 'complaint.claim.wizard'
    _description = 'Complaint Claim Wizard'

    order_id = fields.Many2one(
        'sale.order',
        string='Order',
        readonly=True,
        required=True,
    )
    description = fields.Text(
        string='Description',
        required=True,
    )
    image = fields.Binary(
        string="Image",
        required=True,
    )
    complaint_claim_source_id = fields.Many2one(
        'complaint.claim.source',
        string='Complaint Claim Source',
        required=True,
    )
    complaint_claim_qa_user_id = fields.Many2one(
        'res.users',
        string='Complaint Claim QA User',
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'aznut_complaint_claim.complaint_claim_qa_user_id'),
    )
    complaint_claim_accounting_user_id = fields.Many2one(
        'res.users',
        string='Complaint Claim Accounting User',
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'aznut_complaint_claim.complaint_claim_accounting_user_id'),
    )
    complaint_claim_manufactory_user_id = fields.Many2one(
        'res.users',
        string='Complaint Claim Manufactory User',
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'aznut_complaint_claim.complaint_claim_manufactory_user_id'),
    )
    complaint_claim_ceo_user_id = fields.Many2one(
        'res.users',
        string='Complaint Claim CEO User',
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'aznut_complaint_claim.complaint_claim_ceo_user_id'),
    )

    def action_confirm(self):
        users = self.env['res.users']
        for user in USERS:
            if hasattr(self, user) and getattr(self, user):
                users |= getattr(self, user)
        if users:
            partners = users.mapped('partner_id')
            complaint_claim = self.env['complaint.claim'].sudo().create({
                'image': self.image,
                'description': self.description,
                'complaint_claim_source_id': self.complaint_claim_source_id.id,
                'order_id': self.order_id.id,
                'signature_line_ids': [(0, 0, {
                    'user_id': user.id,
                }) for user in users]
            })
            manufacture_partner_id = self.complaint_claim_manufactory_user_id.partner_id
            if manufacture_partner_id:
                partners |= manufacture_partner_id
            template = self.env.ref('aznut_complaint_claim.complaint_claim_assign_mail')
            base_url = self.get_base_url()
            menu_id = self.env.ref('aznut_complaint_claim.menu_complaint_claim_main').id
            action_id = self.env.ref('aznut_complaint_claim.action_complaint_claim').id
            secondary_url = 'web#id=%s&menu_id=%s&action=%s&model=complaint.claim&view_type=form' % (
                complaint_claim.id, menu_id, action_id
            )
            url = url_join(base_url, secondary_url)

            if template:
                template.with_context(claim_url=url, partner_to=', '.join(
                    str(partner_id) for partner_id in partners.ids)).sudo().send_mail(
                    complaint_claim.id,
                    notif_layout='mail.mail_notification_light',
                )
        else:
            raise ValidationError('No Users For Assigning Complaint Claim!')
