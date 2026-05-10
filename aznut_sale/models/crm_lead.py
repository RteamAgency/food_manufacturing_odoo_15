from odoo import models, api, _, fields

from datetime import timedelta


class CrmLead(models.Model):
    _inherit = "crm.lead"

    invoice_count = fields.Integer(
        compute='_compute_account_move_data',
        string="Number of Invoices",
    )

    def _compute_account_move_data(self):
        for lead in self:
            lead.invoice_count = self.env['account.move'].search_count([
                ('opportunity_id', '=', lead.id)
            ])

    @api.depends('email_from', 'partner_id', 'contact_name', 'partner_name')
    def _compute_potential_lead_duplicates(self):
        super(CrmLead, self.sudo())._compute_potential_lead_duplicates()

    def _handle_won_lost(self, vals):
        super(CrmLead, self)._handle_won_lost(vals)
        for lead in self:
            if 'stage_id' in vals:
                quality_lines = self.env['crm.lead.quality'].search([('trigger_stage_id', '=', vals.get('stage_id'))],
                                                                    order='sequence desc')
                for line in quality_lines:
                    if line.quality_type == 'log_note':
                        lead.message_post(body=line.description)
                    elif line.quality_type == 'activity':
                        days = line.due_value if line.due_type == 'days' else line.due_value * 7
                        due_date = fields.Date.today() + timedelta(days=days)
                        self.env['mail.activity'].create({
                            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                            'user_id': line.user_id.id,
                            'res_id': lead.id,
                            'res_model_id': self.env.ref('crm.model_crm_lead').id,
                            'note': line.description,
                            'date_deadline': due_date,
                            'summary': line.name
                        })

    def action_account_move_new(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action['context'] = {
            'default_partner_id': self.partner_id.id,
            'default_campaign_id': self.campaign_id.id,
            'default_medium_id': self.medium_id.id,
            'default_invoice_origin': self.name,
            'default_source_id': self.source_id.id,
            'default_company_id': self.company_id.id or self.env.company.id,
            'default_move_type': 'out_invoice',
            'default_opportunity_id': self.id,

        }
        if self._context.get('open_invoices'):
            action['domain'] = [('opportunity_id','=',self.id)]
        else:
            action['view_mode'] = 'form'
            action['views'] = [[False, 'form']]
        if self.team_id:
            action['context']['default_team_id'] = self.team_id.id,
        if self.user_id:
            action['context']['default_invoice_user_id'] = self.user_id.id
        return action


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    @api.depends('is_membership_multi', 'member_ids')
    def _compute_member_warning(self):
        self.member_warning = False
        if all(team.is_membership_multi for team in self):
            return
        for team in self:
            member_warning = False
            other_memberships = self.env['crm.team.member'].search([
                ('crm_team_id', '!=', team.id if team.ids else False),  # handle NewID
                ('user_id', 'in', team.sudo().member_ids.ids)
            ])
            if other_memberships and len(other_memberships) == 1:
                member_warning = _(
                    "Adding %(user_name)s in this team would remove him/her from its current team %(team_name)s.",
                    user_name=other_memberships.user_id.name,
                    team_name=other_memberships.crm_team_id.name
                )
            elif other_memberships:
                member_warning = _(
                    "Adding %(user_names)s in this team would remove them from their current teams (%(team_names)s).",
                    user_names=", ".join(other_memberships.mapped('user_id.name')),
                    team_names=", ".join(other_memberships.mapped('crm_team_id.name'))
                )
            if member_warning:
                team.member_warning = member_warning + " " + _(
                    "To add a Salesperson into multiple Teams, activate the Multi-Team option in settings.")
