from odoo import models, fields, api
from odoo.exceptions import UserError


class MainProductCalculator(models.Model):
    _inherit = 'main.product.calculator'

    calculator_status = fields.Selection(
        [('new', 'New'), ('signed_by_seller', 'Signed By Seller'), ('signed_by_customer', 'Signed By Customer'), ('cancelled', 'Cancelled')],
        string='Status',
    )
    signature = fields.Image(
        'Signature',
        copy=False,
        attachment=True,
        max_width=1024,
        max_height=1024)
    signed_by = fields.Char(
        'Signed By',
        copy=False)
    signed_on = fields.Date(
        'Signed On',
        copy=False)
    company_signature = fields.Binary(
        'Company Signature'
    )
    company_signed_on = fields.Date(
        'Company Signature Date'
    )
    is_locked = fields.Boolean(
        string='Is Locked',
    )
    commission = fields.Float(
        related='active_calculator_id.commission',
        store=True,
        readonly=False,
    )

    def _get_report_base_filename(self):
        self.ensure_one()
        return self.name

    def _compute_access_url(self):
        super(MainProductCalculator, self)._compute_access_url()
        for rec in self:
            rec.access_url = '/my/quotes_calc/%s' % (rec.id)

    def get_breadcrumb_quote_name(self):
        return self.display_name.replace('/', ' ')

    def company_sign_quote(self):
        company_signature = self.env.ref(
            'aznut_calculator_sign_quote.product_calculator_settings_sign').company_signature
        if company_signature:
            self.company_signature = company_signature
            self.company_signed_on = fields.Date.today()
            if self.calculator_status != 'signed_by_customer':
                self.calculator_status = 'signed_by_seller'
        else:
            raise UserError('Company signature missing')

    def action_lock_unlock(self):
        self.ensure_one()
        if self._context.get('lock_action') == 'lock':
            self.is_locked = True
        if self._context.get('lock_action') == 'unlock':
            self.is_locked = False

    def manage_custom_calculator(self):
        self.ensure_one()
        if self.is_locked:
            raise UserError('Contact Administrator to unlock the Calculator')
        return super(MainProductCalculator, self).manage_custom_calculator()

    def copy_child_calculator(self):
        self.ensure_one()
        if self.is_locked:
            raise UserError('Contact Administrator to unlock the Calculator')
        return super(MainProductCalculator, self).copy_child_calculator()

    def action_cancel(self):
        self.write({'calculator_status': 'cancelled'})

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        rec = super(MainProductCalculator, self).copy(default)
        rec.write({
            'company_signature': False,
            'company_signed_on': False
        })
        return rec


class ProductCalculator(models.Model):
    _inherit = 'product.calculator'

    def _default_commission(self):
        user = self.env.user
        default_commission = self.env.ref('aznut_calculator.product_calculator_settings_main').commission
        commission_group = self.env['product.calculator.profit.group'].search([
            ('users_ids', '=', user.id)
        ])[:1]
        if commission_group:
            return commission_group.calculator_profit
        return default_commission

    commission = fields.Float(
        string='Commission',
        digits=(16, 2),
        default=_default_commission,

    )

    def _compute_ready_jar_cost_discount_amount(self):
        self.ready_jar_cost = False
        for rec in self:
            shape_cost = sum(rec.shape_ids.mapped('cost'))
            ready_jar_cost = sum([rec.total_cost, rec.jar_price, rec.box_price, rec.profit, rec.commission,
                                  rec.shipping, rec.label_price, rec.shrink_price, rec.operating_expenses,
                                  shape_cost, rec.lid_price, rec.taxes]) - rec.discount_amount
            rec.ready_jar_cost = ready_jar_cost
