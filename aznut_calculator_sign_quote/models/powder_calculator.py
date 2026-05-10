from odoo import models, fields, api
from odoo.exceptions import UserError


class MainPowderCalculator(models.Model):
    _inherit = 'main.powder.calculator'

    calculator_status = fields.Selection(
        [('new', 'New'), ('signed_by_seller', 'Signed By Seller'), ('signed_by_customer', 'Signed By Customer'), ('cancelled', 'Cancelled')],
        string='Status',
        default='new',
        readonly=True,
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
        'Company Signature',
        copy=False,
    )
    company_signed_on = fields.Date(
        'Company Signature Date',
        copy=False,
    )
    is_locked = fields.Boolean(
        string='Is Locked',
    )
    commission = fields.Float(
        related='active_powder_calculator_id.commission',
        store=True,
        readonly=False,
    )

    def _compute_access_url(self):
        super(MainPowderCalculator, self)._compute_access_url()
        for rec in self:
            rec.access_url = '/my/powder_quotes_calc/%s' % rec.id

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

    def action_cancel(self):
        self.write({'calculator_status': 'cancelled'})

    def action_lock_unlock(self):
        self.ensure_one()
        if self._context.get('lock_action') == 'lock':
            self.is_locked = True
        if self._context.get('lock_action') == 'unlock':
            self.is_locked = False

    def copy_child_calculator(self):
        self.ensure_one()
        if self.is_locked:
            raise UserError('Contact Administrator to unlock the Calculator')
        return super(MainPowderCalculator, self).copy_child_calculator()


class PowderCalculator(models.Model):
    _inherit = 'powder.calculator'

    def _default_commission(self):
        user = self.env.user
        default_commission = self.env.ref('aznut_calculator.powder_calculator_settings_main').commission
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

    def _compute_price_per_jar(self):
        super(PowderCalculator, self)._compute_price_per_jar()
        for powder_calculator in self:
            powder_calculator.price_per_jar += powder_calculator.commission
            powder_calculator.total_price = powder_calculator.price_per_jar * powder_calculator.count_of_jars


class PowderCalculatorSettings(models.Model):
    _inherit = 'powder.calculator.settings'

    commission = fields.Float(
        string='Commission',
        digits=(16, 2),
    )
