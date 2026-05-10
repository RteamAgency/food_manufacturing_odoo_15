from odoo import models, api, tools
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.constrains('name')
    def _check_unique_name(self):
        for partner in self.filtered(lambda pt: pt.name):
            other_partners = self.env['res.partner'].sudo().search([
                ('name', '=', partner.name),
                ('id', '!=', partner.id)
            ])
            if other_partners:
                raise ValidationError(
                    'Field name (%s) already exists in %s other partners!' % (partner.name, len(other_partners)))

    @api.constrains('phone')
    def _check_unique_phone(self):
        for partner in self.filtered(lambda pt: pt.phone):
            other_partners = self.env['res.partner'].sudo().search([
                ('phone', '=', partner.phone),
                ('id', '!=', partner.id)
            ])
            if other_partners:
                raise ValidationError(
                    'Field phone (%s) already exists in these partners: %s!' % (partner.phone, ', '.join(
                        other_partners.mapped('display_name'))))

    @api.constrains('email')
    def _check_unique_email(self):
        for partner in self.filtered(lambda pt: pt.email):
            other_partners = self.env['res.partner'].sudo().search([
                ('email', '=', partner.email),
                ('id', '!=', partner.id)
            ])
            if other_partners:
                raise ValidationError(
                    'Field email (%s) already exists in these partners: %s!' % (partner.email, ', '.join(
                        other_partners.mapped('display_name'))))

    def _get_name(self):
        return super(ResPartner, self.sudo())._get_name()

    def mail_partner_format(self):
        return super(ResPartner, self.sudo()).mail_partner_format()

    @api.depends('name', 'email')
    def _compute_email_formatted(self):
        self = self.sudo()
        self.email_formatted = False
        for partner in self:
            emails_normalized = tools.email_normalize_all(partner.email)
            if emails_normalized:
                partner.email_formatted = tools.formataddr((
                    partner.name or u"False",
                    ','.join(emails_normalized)
                ))
            elif partner.email:
                partner.email_formatted = tools.formataddr((
                    partner.name or u"False",
                    partner.email
                ))
