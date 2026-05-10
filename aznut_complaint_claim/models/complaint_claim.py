from odoo import fields, models, api


class ComplaintClaim(models.Model):
    _name = 'complaint.claim'
    _description = 'Complaint Claim'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Name',
        readonly=True,
    )
    order_id = fields.Many2one(
        'sale.order',
        string='Order',
        readonly=True,
    )
    description = fields.Text(
        string='Description',
        readonly=True,
    )
    image = fields.Binary(
        string="Image",
        readonly=True,
    )
    complaint_claim_source_id = fields.Many2one(
        'complaint.claim.source',
        string='Complaint Claim Source',
        readonly=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('closed', 'Closed')],
        string='Status',
        group_expand='_expand_state',
        compute='_compute_state',
        store=True,
        default='draft',
        tracking=True,
    )
    complaint_claim_qa_user_id = fields.Many2one(
        'res.users',
        string='Complaint Claim QA User',
    )
    signature_line_ids = fields.One2many(
        'complaint.claim.signature.line',
        'complaint_claim_id',
        string='Signature Lines',
    )

    @api.depends('signature_line_ids.signature')
    def _compute_state(self):
        for complaint_claim in self:
            if not complaint_claim.signature_line_ids.filtered(lambda line: not line.signature):
                complaint_claim.state = 'closed'

    @api.model
    def create(self, vals):
        if 'name' not in vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('complaint.claim') or 'New'
        return super(ComplaintClaim, self).create(vals)

    def _expand_state(self, *args, **kwargs):
        return [key for key, val in self._fields['state'].selection]


class ComplaintClaimSignLine(models.Model):
    _name = 'complaint.claim.signature.line'
    _description = 'Complaint Claim Sign Line'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        readonly=True,
    )
    signature = fields.Binary(
        string="Digital Signature"
    )
    complaint_claim_id = fields.Many2one(
        'complaint.claim',
        string='Complaint Claim',
    )
    can_sign = fields.Boolean(
        string='Can Sign',
        compute='_compute_can_sign',
    )
    sign_date = fields.Datetime(
        string='Sign Date',
        readonly=True,
    )

    @api.onchange('signature')
    def _onchange_signature(self):
        if self.signature:
            self.sign_date = fields.Datetime.now()

    @api.depends('signature')
    def _compute_can_sign(self):
        self.can_sign = False
        for line in self:
            if not line.signature and line.user_id.id == self.env.user.id:
                line.can_sign = True
