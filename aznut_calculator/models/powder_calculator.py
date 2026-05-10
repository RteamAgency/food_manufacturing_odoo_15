from odoo import fields, models, api
from odoo.exceptions import ValidationError

from odoo.tools import formatLang

from markupsafe import Markup
from datetime import timedelta
from lxml import html as lxml_html

from .product_calculator import check_ingredients_is_unique, get_ingredients_table, \
    get_mail_action, generate_total_table, get_default, calculate_seq_number, send_approval_mail, get_cleaned_note
from .ask_gpt import get_gpt_session_window, CHAT_TEMPLATE
from .product_calculator import calculator_salesperson_read_group, calculator_salesperson_search

order_details_fields = ['count_of_jars', 'jar_exist', 'lid_exist', 'label_exist', 'jar_product_id', 'lid_product_id',
                        'label_finish', 'scoop_grams',
                        'ordered_jars_number', 'jar_size_oz']
order_details_names = ['Count of Jars', 'Jar', 'Lid', 'Label', 'Jar Finish', 'Lid Finish',
                       'Label Finish', 'Each Scoop Size', 'Scoops per jar',
                       'Jar Weight']


def compare_with_relative_tolerance(value1, value2, relative_tolerance=0.0001):
    if value1 == 0 or value2 == 0:
        return abs(value1 - value2) <= relative_tolerance
    return abs(value1 - value2) <= relative_tolerance * max(abs(value1), abs(value2))


class MainPowderCalculator(models.Model):
    _name = 'main.powder.calculator'
    _description = 'Main Powder Calculator'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(
        string='Name',
        default='New',
        readonly=True,
        copy=False,
    )
    lead_user_id = fields.Many2one(
        'res.users',
        store=True,
        compute='_compute_lead_user_id',
    )
    powder_calculator_ids = fields.One2many(
        'powder.calculator',
        'main_powder_calculator',
        string='Calculators',
        readonly=True,
    )
    products_ids = fields.Many2many(
        'product.product',
        string='Products',
        copy=False,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
    )
    allowed_partner_ids = fields.Many2many(
        'res.partner',
        compute='_compute_allowed_partners'
    )
    lead_id = fields.Many2one(
        'crm.lead',
        string='Opportunity',
    )
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('sent', 'Sent'), ],
        default='draft',
        copy=False,
    )
    active_powder_calculator_id = fields.Many2one(
        'powder.calculator',
        string='Active Calculator',
        copy=False,
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        index=True,
        default=lambda self: self.env.company)
    user_id = fields.Many2one(
        'res.users',
        'User',
        default=lambda self: self.env.user.id,
        copy=False,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.user.company_id.currency_id,
        copy=False,
    )

    # child calculators
    product_name = fields.Char(
        related='active_powder_calculator_id.product_name',
    )
    scoop_grams = fields.Float(
        related='active_powder_calculator_id.scoop_grams',
        store=True,
        readonly=False,
    )
    ordered_jars_number = fields.Integer(
        related='active_powder_calculator_id.ordered_jars_number',
        store=True,
        readonly=False,
    )
    packaging_materials = fields.Float(
        related='active_powder_calculator_id.packaging_materials',
        store=True,
        readonly=False,
    )
    operating_expenses = fields.Float(
        related='active_powder_calculator_id.operating_expenses',
    )
    profit = fields.Float(
        related='active_powder_calculator_id.profit',
        store=True,
        readonly=False,
    )
    active_ingredient_ids = fields.One2many(
        related='active_powder_calculator_id.active_ingredient_ids',
        readonly=False,
        inverse='_inverse_active_ingredient_ids',
    )
    total_ingredients_scoop_cost = fields.Char(
        related='active_powder_calculator_id.total_ingredients_scoop_cost',
    )
    active_in_jar = fields.Float(
        related='active_powder_calculator_id.active_in_jar',
    )
    ingredients_cost = fields.Float(
        related='active_powder_calculator_id.ingredients_cost',
    )
    ready_jar_cost = fields.Float(
        related='active_powder_calculator_id.ready_jar_cost',
    )
    total_price = fields.Float(
        related='active_powder_calculator_id.total_price',
    )
    bom_count = fields.Integer(
        string='BoM Count',
        compute='_compute_bom_count',
    )
    note = fields.Html(
        related='active_powder_calculator_id.note',
        store=True,
        readonly=False,
    )
    discount_amount = fields.Float(
        related='active_powder_calculator_id.discount_amount',
        store=True,
        readonly=False,
    )
    jar_size_gr = fields.Float(
        related='active_powder_calculator_id.jar_size_gr',
    )
    jar_size_oz = fields.Float(
        related='active_powder_calculator_id.jar_size_oz',
    )
    count_of_jars = fields.Integer(
        related='active_powder_calculator_id.count_of_jars',
        store=True,
        readonly=False,
    )
    use_active_multiply = fields.Boolean(
        string="Add 15% to active quantity output",
    )
    jar_price = fields.Float(
        related='active_powder_calculator_id.jar_price',
        store=True,
        readonly=False,
    )
    lid_price = fields.Float(
        related='active_powder_calculator_id.lid_price',
        store=True,
        readonly=False,
    )
    box_price = fields.Float(
        related='active_powder_calculator_id.box_price',
        store=True,
        readonly=False,
    )
    label_price = fields.Float(
        related='active_powder_calculator_id.label_price',
        store=True,
        readonly=False,
    )
    shrink_price = fields.Float(
        related='active_powder_calculator_id.shrink_price',
        store=True,
        readonly=False,
    )
    label_exist = fields.Boolean(
        related='active_powder_calculator_id.label_exist',
        store=True,
        readonly=False,
    )
    label_finish = fields.Selection(
        related='active_powder_calculator_id.label_finish',
        store=True,
        readonly=False,
    )
    jar_exist = fields.Boolean(
        related='active_powder_calculator_id.jar_exist',
        store=True,
        readonly=False,
    )
    jar_product_id = fields.Many2one(
        related='active_powder_calculator_id.jar_product_id',
        store=True,
        readonly=False,
    )
    lid_exist = fields.Boolean(
        related='active_powder_calculator_id.lid_exist',
        store=True,
        readonly=False,
    )
    lid_product_id = fields.Many2one(
        related='active_powder_calculator_id.lid_product_id',
        store=True,
        readonly=False,
    )
    monthly_exp = fields.Integer(
        related='active_powder_calculator_id.monthly_exp',
        store=True,
        readonly=False,
    )
    jars_per_month = fields.Integer(
        related='active_powder_calculator_id.jars_per_month',
        store=True,
        readonly=False,
    )
    price_per_jar = fields.Float(
        related='active_powder_calculator_id.price_per_jar',
    )
    bacteria_gram = fields.Float(
        related='active_powder_calculator_id.bacteria_gram',
        store=True,
        readonly=False,
    )
    bacteria_gram_base = fields.Integer(
        related='active_powder_calculator_id.bacteria_gram_base',
    )
    bacteria_gram_exponent = fields.Integer(
        related='active_powder_calculator_id.bacteria_gram_exponent',
    )
    cfu_portion = fields.Float(
        related='active_powder_calculator_id.cfu_portion',
        store=True,
        readonly=False,
    )
    cfu_portion_uom = fields.Selection(
        related='active_powder_calculator_id.cfu_portion_uom',
        store=True,
        readonly=False,
    )
    probiotic_portion = fields.Float(
        related='active_powder_calculator_id.probiotic_portion',
    )
    moq = fields.Integer(
        related='active_powder_calculator_id.moq',
    )
    total_ingredients_bom_lb_theory = fields.Float(
        related='active_powder_calculator_id.total_ingredients_bom_lb_theory',
    )
    total_ingredients_bom_lb_actual = fields.Float(
        related='active_powder_calculator_id.total_ingredients_bom_lb_actual',
    )
    verification_lb = fields.Boolean(
        related='active_powder_calculator_id.verification_lb',
    )
    shipping = fields.Float(
        related='active_powder_calculator_id.shipping',
    )
    taxes = fields.Float(
        related='active_powder_calculator_id.taxes',
        store=True,
        readonly=False,
    )
    jar_products_ids = fields.Many2many(
        'product.product',
        related='active_powder_calculator_id.jar_products_ids',
    )
    box_product_id = fields.Many2one(
        related='active_powder_calculator_id.box_product_id',
        store=True,
        readonly=False,
    )
    shrink_product_id = fields.Many2one(
        related='active_powder_calculator_id.shrink_product_id',
        store=True,
        readonly=False,
    )
    ask_gpt_session_id = fields.Many2one(
        related='active_powder_calculator_id.ask_gpt_session_id',
    )
    procurement_partner_id = fields.Many2one(
        related='active_powder_calculator_id.procurement_partner_id',
        store=True,
        readonly=False,
    )
    procurement_reply = fields.Html(
        related='active_powder_calculator_id.procurement_reply',
    )
    is_user_calculator_procurement = fields.Boolean(
        string='Is User Calculator Procurement',
        compute="_compute_is_user_calculator_procurement",
    )
    manufacturing_partner_id = fields.Many2one(
        related='active_powder_calculator_id.manufacturing_partner_id',
        store=True,
        readonly=False,
    )
    manufacturing_reply = fields.Html(
        related='active_powder_calculator_id.manufacturing_reply',
    )
    calculator_product_category_id = fields.Many2one(
        'product.category',
        string='Calculator Product Category',
        default=lambda rec: get_default(rec, 'aznut_calculator.powder_calculator_settings_main',
                                        'calculator_product_category_id'),
    )
    approval_partner_id = fields.Many2one(
        'res.partner',
        related='active_powder_calculator_id.approval_partner_id',
    )
    approval_email_sent = fields.Boolean(
        related='active_powder_calculator_id.approval_email_sent',
    )
    show_approval_button = fields.Boolean(
        string='Show Approval Button',
        compute='_compute_show_approval_button',
    )
    is_calculator_salesperson = fields.Boolean(
        string='Is Calculator Salesperson',
        compute='_compute_is_calculator_salesperson',
    )
    allowed_calculators_ids = fields.Many2many(
        'powder.calculator',
        'allowed_calculators_rel',
        compute='_compute_allowed_calculators_ids',
    )

    @api.onchange('active_ingredient_ids')
    def _onchange_active_ingredient_ids(self):
        self.active_ingredient_ids._compute_seq_number()

    @api.onchange('box_product_id')
    def _onchange_box_product_id(self):
        self.box_price = self.box_product_id.standard_price * (self.box_product_id.calculator_uom_id.ratio or 1)

    @api.onchange('shrink_product_id')
    def _onchange_shrink_product_id(self):
        self.shrink_price = self.shrink_product_id.standard_price

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.lead_id.partner_id = self.partner_id

    @api.onchange('label_exist', 'jar_exist', 'lid_exist')
    def _onchange_label_or_jar(self):
        if not self.label_exist:
            self.label_finish = False
        if not self.jar_exist:
            self.jar_product_id = False
        if not self.lid_exist:
            self.lid_product_id = False

    @api.onchange('jar_product_id')
    def _onchange_jar_product(self):
        self.jar_price = self.jar_product_id.standard_price

    @api.onchange('label_exist')
    def _onchange_label_exist(self):
        label_preset = self.env.ref('aznut_calculator.powder_calculator_settings_main').label_preset
        for rec in self:
            rec.label_price = label_preset if rec.label_exist else 0

    @api.onchange('lid_product_id')
    def _onchange_lid_product(self):
        self.lid_price = self.lid_product_id.standard_price

    def _compute_is_calculator_salesperson(self):
        calculator_salesperson = self.env.user.has_group('aznut_calculator.group_calculator_salesperson')
        self.is_calculator_salesperson = calculator_salesperson

    def _compute_show_approval_button(self):
        self.show_approval_button = False
        for main_calculator in self:
            if main_calculator.approval_email_sent and (
                    main_calculator.approval_partner_id == self.env.user.partner_id or self.env.user.has_group(
                'base.group_system')):
                main_calculator.show_approval_button = True

    @api.depends('lead_id.user_id')
    def _compute_lead_user_id(self):
        for main_calculator in self:
            main_calculator.lead_user_id = main_calculator.lead_id.user_id

    @api.depends('powder_calculator_ids')
    def _compute_allowed_calculators_ids(self):
        for main_calculator in self:
            allowed_calculators_ids = main_calculator.powder_calculator_ids
            if main_calculator.is_calculator_salesperson:
                allowed_calculators_ids = allowed_calculators_ids.filtered(
                    lambda calculator: calculator.create_uid.id == self.env.user.id)
            main_calculator.allowed_calculators_ids = allowed_calculators_ids

    @api.depends('partner_id')
    def _compute_allowed_partners(self):
        calculator_manager = self.env.user.has_group('aznut_calculator.group_calculator_manager')
        for rec in self:
            if calculator_manager:
                rec.allowed_partner_ids = self.env['res.partner'].search([])
            else:
                rec.allowed_partner_ids = [self.env.user.partner_id.id]

    def _compute_is_user_calculator_procurement(self):
        calculator_procurement = self.env.user.has_group('aznut_calculator.group_calculator_procurement')
        self.is_user_calculator_procurement = calculator_procurement

    def _compute_bom_count(self):
        for rec in self:
            rec.bom_count = self.env['mrp.bom'].search_count(
                [('powder_calculator_id', 'in', rec.powder_calculator_ids.ids)])

    def _inverse_active_ingredient_ids(self):
        for main_calculator in self:
            main_calculator.active_powder_calculator_id.active_ingredient_ids = main_calculator.active_ingredient_ids

    def copy_child_calculator(self):
        self.ensure_one()
        view_id = self.env.ref('aznut_calculator.copy_powder_calculator_wizard_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Copy Child Calculator',
            'view_mode': 'form',
            'res_model': 'copy.powder.calculator.wizard',
            'target': 'new',
            'view_id': view_id,
            'context': {
                'default_main_calculator_id': self.id,
                'default_calculator_id': self.active_powder_calculator_id.id,
            }
        }

    def create_opportunity(self):
        self.ensure_one()
        lead = self.sudo().lead_id
        if not lead:
            created_lead = self.env['crm.lead'].sudo().create({
                'name': self.display_name,
                'user_id': self.user_id.id,
                'partner_id': self.partner_id.id,
                'type': 'opportunity',
                'main_powder_calculator_id': self.id,
            })
            self.lead_id = created_lead.id

    def show_lead(self):
        self.ensure_one()
        view_id = self.env.ref('crm.crm_lead_view_form').id
        return {
            'name': 'Lead',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'create': 0},
            'res_id': self.lead_id.id,
        }

    def _get_expiry_date(self):
        self.ensure_one()
        return self.create_date + timedelta(days=15)

    def send_by_email(self):
        self.ensure_one()
        template_id = self.env['ir.model.data']._xmlid_to_res_id('aznut_calculator.main_powder_calculator_email',
                                                                 raise_if_not_found=False)
        template = self.env['mail.template'].browse(template_id)
        if template.lang:
            lang = template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'main.powder.calculator',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_as_sent': True,
            'custom_layout': "mail.mail_notification_light",
            'force_email': True,
            'model_description': self.with_context(lang=lang).display_name
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def create_bom(self):
        main_wizard = self.env['powder.calculator.create.bom.wizard'].create({})
        lb_uom = self.env.ref('uom.product_uom_lb')
        self.ensure_one()
        for powder_calculator in self.powder_calculator_ids.filtered(lambda rec: not rec.result_product_tmpl_id):
            create_bom_wizard_lines_ids = []
            for active_ingredient in powder_calculator.active_ingredient_ids:
                create_bom_wizard_lines_ids.append(self.env['create.bom.wizard.line'].create({
                    'product_id': active_ingredient.product_id.id,
                    'quantity': active_ingredient.total_bom_lb,
                    'uom_id': lb_uom.id,
                }).id)
            self.env['create.bom.wizard.powder'].create({
                'create_bom_wizard_lines_ids': create_bom_wizard_lines_ids,
                'calculator_id': powder_calculator.id,
                'main_wizard_id': main_wizard.id,
            })
        view_id = self.env.ref('aznut_calculator.powder_calculator_create_bom_wizard_form_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create BoM',
            'view_mode': 'form',
            'res_model': 'powder.calculator.create.bom.wizard',
            'target': 'new',
            'view_id': view_id,
            'res_id': main_wizard.id,
        }

    def show_boms(self):
        self.ensure_one()
        return {
            'name': 'BoMs',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.bom',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('mrp.mrp_bom_tree_view').id, 'tree'),
                      (self.env.ref('mrp.mrp_bom_form_view').id, 'form')],
            'target': 'current',
            'domain': [('powder_calculator_id', 'in', self.powder_calculator_ids.ids)],
            'context': {'create': 0},
        }

    def action_add_moq_discount(self):
        self.ensure_one()
        if self.moq:
            moq_dividers = self.env['powder.calculator.moq.discount'].search([])
            if not moq_dividers:
                raise ValidationError('Please specify MOQ Discount dividers')
            count_ratio = self.count_of_jars / self.moq
            dividers = []
            deduct_coef = 0
            use_coef = False
            for rec in moq_dividers:
                record_data = {
                    'divider': rec.divider,
                    'moq_discount': rec.moq_discount
                }
                dividers.append(record_data)
            sorted_dividers = sorted(dividers, key=lambda x: x['divider'], reverse=True)
            for line in sorted_dividers:
                if count_ratio >= line.get('divider'):
                    deduct_coef = line.get('moq_discount')
                    use_coef = True
                    break
            if not use_coef:
                raise ValidationError('MOQ Discount is not available for this calculator')
            self.discount_amount = deduct_coef

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if not kwargs.get('partner_ids') and kwargs.get(
                'subtype_xmlid') != 'mail.mt_comment' and not self.env.context.get('activity_mail'):
            raise ValidationError('Partner email is not set')
        if self.env.context.get('mark_as_sent'):
            if self.lead_id:
                self.lead_id.message_post(body=kwargs.get('body'), attachment_ids=kwargs.get('attachment_ids'))
            self.state = 'sent'
        return super(MainPowderCalculator, self.with_context(
            mail_post_autofollow=self.env.context.get('mail_post_autofollow', True))).message_post(**kwargs)

    def action_open_compare_wizard(self):
        self.ensure_one()
        view = self.env.ref('aznut_calculator.powder_compare_calculator_wizard_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Compare Powder Calculators',
            'view_mode': 'form',
            'res_model': 'powder.compare.calculator.wizard',
            'target': 'new',
            'view_id': view.id,
            'context': {
                'default_main_calculator_id': self.id,
                'default_calculator_first': self.active_powder_calculator_id.id,
            }
        }

    def action_open_calculators_costs(self):
        self.ensure_one()
        view = self.env.ref('aznut_calculator.powder_calculator_tree_view')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Calculators Costs',
            'view_mode': 'tree',
            'res_model': 'powder.calculator',
            'target': 'new',
            'domain': [('id', 'in', self.powder_calculator_ids.ids)],
            'view_id': view.id,
        }

    def action_approve_calculator(self):
        self.mapped('active_powder_calculator_id').write({
            'approval_email_sent': False,
        })

    def write(self, values):
        rec = super(MainPowderCalculator, self).write(values)
        self._update_calculators()
        return rec

    @api.model
    def create(self, vals):
        if 'name' not in vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('main.powder.calculator') or 'New'
        rec = super(MainPowderCalculator, self).create(vals)
        rec._update_calculators()
        lead_id = vals.get('lead_id', False)
        if lead_id:
            lead = self.env['crm.lead'].sudo().browse(lead_id).exists()
            lead.main_powder_calculator_id = rec.id
        return rec

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        rec = super(MainPowderCalculator, self).copy(default)
        products = self.products_ids
        calculators = self.env['powder.calculator'].browse([i.copy().id for i in self.powder_calculator_ids])
        vals = {
            'powder_calculator_ids': calculators,
            'products_ids': products.ids,
        }
        rec.write(vals)
        return rec

    def unlink(self):
        self.powder_calculator_ids.unlink()
        return super(MainPowderCalculator, self).unlink()

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        return super(MainPowderCalculator, self)._search(calculator_salesperson_search(self, args), offset, limit,
                                                         order, count, access_rights_uid)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        return super(MainPowderCalculator, self).read_group(calculator_salesperson_read_group(self, domain), fields,
                                                            groupby, offset=offset, limit=limit,
                                                            orderby=orderby, lazy=lazy)

    def _update_calculators(self):
        for main_calculator in self:
            existing_calculators = self.env['powder.calculator']
            for product in main_calculator.products_ids:
                existing_calculator = main_calculator.powder_calculator_ids.filtered(
                    lambda c: c.product_id == product)[:1]
                if not existing_calculator:
                    existing_calculator = self.env['powder.calculator'].create({
                        'product_id': product.id,
                        'main_powder_calculator': main_calculator.id,
                    })
                    bom_id = product.bom_ids[:1]
                    if bom_id:
                        existing_calculator.write({
                            'active_ingredient_ids': [(0, 0, {
                                'quantity': bom_line.product_qty,
                                'product_id': bom_line.product_id.id,
                            }) for bom_line in bom_id.bom_line_ids]
                        })
                    main_calculator.powder_calculator_ids = [(4, existing_calculator.id)]
                existing_calculators = existing_calculators | existing_calculator
            calculators_to_delete = main_calculator.powder_calculator_ids - existing_calculators
            if calculators_to_delete:
                calculators_to_delete.unlink()

    def action_generate_ask_gpt_session(self):
        self.ensure_one()
        if not self.ask_gpt_session_id:
            self.env['ask.gpt.session'].sudo().create({
                'powder_calculator_id': self.active_powder_calculator_id.id,
            })

    def action_open_ask_gpt_session(self):
        self.ensure_one()
        if self.ask_gpt_session_id:
            res = get_gpt_session_window(self.env.ref('aznut_calculator.ask_gpt_session_form').id,
                                         self.ask_gpt_session_id.id)
            res.update({'context': {'from_calculator': True}})
            return res

    def action_send_procurement_mail(self):
        self.ensure_one()
        body = self.env.ref('aznut_calculator.support_settings_main').procurement_text
        if '%name%' in body:
            body = body.replace('%name%', self.procurement_partner_id.name or '')
        if '%ingredients%' in body:
            table = get_ingredients_table(
                self.active_ingredient_ids.filtered(lambda ing: ing.forecast_availability < 0), 'product_id',
                'total_bom_lb', 'lb_uom_id', vendors=True, ing_type='active')
            if table:
                body = body.replace('%ingredients%', Markup(table))
        return get_mail_action(self.active_powder_calculator_id, self.display_name, body, self.procurement_partner_id,
                               self.active_ingredient_ids.filtered(lambda ing: ing.forecast_availability < 0))

    def action_send_approval_mail(self):
        send_approval_mail(self.mapped('active_powder_calculator_id'), 'main.powder.calculator')

    def action_send_manufacturing_mail(self):
        self.ensure_one()
        body = self.env.ref('aznut_calculator.support_settings_main').manufacturing_text
        if '%name%' in body:
            body = body.replace('%name%', self.manufacturing_partner_id.name or '')
        if '%ingredients%' in body:
            total_string = f"""
                   <div>
                       <span style="white-space: nowrap; font-weight: bold;">
                           {"{:.4f}".format(self.total_ingredients_bom_lb_actual)}
                       </span>
                   </div>
                   <div style="border-bottom: 1px solid black; width: 100%; margin: 0 auto;"/>
                   <div>
                       <span style="white-space: nowrap; font-weight: bold;">
                           {"{:.4f}".format(self.total_ingredients_bom_lb_theory)}
                       </span>
                   </div>
                   """
            table = get_ingredients_table(self.active_ingredient_ids, 'product_id', 'total_bom_lb', 'lb_uom_id',
                                          vendors=False, ing_type='active')
            if table:
                body = body.replace('%ingredients%', Markup(table + generate_total_table(
                    ['Cost Ingredients per Scoop', 'Cost Ingredients per Jar', 'Ingredients per BOM (lb)'],
                    [self.total_ingredients_scoop_cost, round(self.active_in_jar, 2), total_string, ])))
        return get_mail_action(self.active_powder_calculator_id, self.display_name, body, self.manufacturing_partner_id,
                               False)


class PowderCalculator(models.Model):
    _name = 'powder.calculator'
    _description = 'Powder Calculator'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.constrains('active_ingredient_ids')
    def _check_ingredients_is_unique(self):
        for rec in self:
            msg = check_ingredients_is_unique({'Active': 'active_ingredient_ids'}, rec)
            if msg:
                raise ValidationError('\n'.join(msg))

    product_id = fields.Many2one(
        'product.product',
        string='Product',
    )
    main_powder_calculator = fields.Many2one(
        'main.powder.calculator',
        string='Main Powder Calculator',
        copy=False,
    )
    product_name = fields.Char(
        string='Product Name',
        compute='_compute_product_name',
    )
    scoop_grams = fields.Float(
        string='Each Scoop Size',
        digits=(16, 1),
        default=lambda rec: get_default(rec, 'aznut_calculator.powder_calculator_settings_main', 'scoop_grams'),
    )
    ordered_jars_number = fields.Integer(
        string='Scoops per jar',
        default=lambda rec: get_default(rec, 'aznut_calculator.powder_calculator_settings_main', 'ordered_jars_number'),
    )
    packaging_materials = fields.Float(
        string='Scoop Cost',
        digits=(16, 2),
        default=lambda rec: get_default(rec, 'aznut_calculator.powder_calculator_settings_main', 'packaging_materials'),
    )
    operating_expenses = fields.Float(
        string='Operating Expenses',
        compute='_compute_operating_expenses'
    )
    profit = fields.Float(
        string='Profit',
        digits=(16, 2),
        default=lambda rec: get_default(rec, 'aznut_calculator.powder_calculator_settings_main', 'profit'),
    )
    active_ingredient_ids = fields.One2many(
        'powder.active.ingredient',
        'powder_calculator_id',
        string='Active Ingredients',
        copy=False,
    )
    total_ingredients_scoop_cost = fields.Char(
        string='Total Ingredients Scoop Cost',
        compute='_compute_totals',
        digits=(16, 4),
    )
    total_ingredients_bom_lb_theory = fields.Float(
        string='Total Ingredients Bom Lb Theory',
        compute="_compute_total_ingredients_bom_lb",
        digits=(16, 4),

    )
    total_ingredients_bom_lb_actual = fields.Float(
        string='Total Ingredients Bom Lb Theory',
        compute="_compute_total_ingredients_bom_lb",
        digits=(16, 4),
    )
    verification_lb = fields.Boolean(
        string='Verification',
        compute="_compute_total_ingredients_bom_lb"
    )
    active_in_jar = fields.Float(
        string='Active In Jar',
        compute='_compute_totals',
        digits=(16, 2),
    )
    ingredients_cost = fields.Float(
        string='Ingredients',
        digits=(16, 2),
        compute='_compute_totals'
    )
    ready_jar_cost = fields.Float(
        string='Net Cost',
        digits=(16, 2),
        compute='_compute_totals'
    )
    total_price = fields.Float(
        string='Total Price',
        digits=(16, 2),
        compute='_compute_price_per_jar'
    )
    result_product_tmpl_id = fields.Many2one(
        'product.template',
        string='Result Product',
        copy=False,
    )
    note = fields.Html(
        string='Note',
    )
    discount_amount = fields.Float(
        string='Discount',
        digits=(16, 2),
    )
    jar_size_gr = fields.Float(
        string='Jar Size (gr)',
        digits=(16, 2),
        compute='_compute_jar_size'
    )
    jar_size_oz = fields.Float(
        string='Jar Size (oz)',
        digits=(16, 1),
        compute='_compute_jar_size'
    )
    jar_price = fields.Float(
        string='Jar',
        digits=(16, 3),
    )
    lid_price = fields.Float(
        string='Lid',
        digits=(16, 3),
    )
    box_price = fields.Float(
        string='Box',
        digits=(16, 3),
        default=lambda rec: get_default(rec, 'aznut_calculator.powder_calculator_settings_main', 'box_preset'),
    )
    label_price = fields.Float(
        string='Label',
        digits=(16, 3),
    )
    shrink_price = fields.Float(
        string='Shrink',
        digits=(16, 3),
        default=lambda rec: get_default(rec, 'aznut_calculator.powder_calculator_settings_main', 'shrink_preset'),
    )
    count_of_jars = fields.Integer(
        string='Count of Jars',
        default=1,
    )
    label_exist = fields.Boolean(
        string='Label',
        default=False,
    )
    label_finish = fields.Selection(
        selection=[('mate', 'Mate'), ('glossy', 'Glossy')],
        string='Label Finish'
    )
    jar_exist = fields.Boolean(
        'Jar',
        default=False,
    )
    jar_product_id = fields.Many2one(
        'product.product',
        string='Jar Finish',
        domain=lambda rec: [
            ('categ_id', '=', rec.env.ref(
                'aznut_calculator.product_calculator_settings_main').dog_treats_packaging_materials_category_id.id)],
    )
    lid_exist = fields.Boolean(
        string='Lid',
    )
    lid_product_id = fields.Many2one(
        'product.product',
        string='Lid Finish',
        domain=lambda rec: [
            ('categ_id', '=', rec.env.ref(
                'aznut_calculator.product_calculator_settings_main').dog_treats_packaging_materials_category_id.id)],
    )
    monthly_exp = fields.Integer(
        string='Monthly Expenses',
        default=lambda rec: get_default(rec, 'aznut_calculator.powder_calculator_settings_main',
                                        'monthly_expenses_preset'),
    )
    jars_per_month = fields.Integer(
        string='Jars Per Month',
        default=lambda rec: get_default(rec, 'aznut_calculator.powder_calculator_settings_main',
                                        'jar_per_months_preset'),
    )
    price_per_jar = fields.Float(
        string='Price per Jar',
        compute='_compute_price_per_jar',
        digits=(16, 2),
    )

    moq = fields.Integer(
        string='MOQ, units',
        compute='_compute_moq',
    )

    bacteria_gram = fields.Float(
        string='Bacteria in 1 gram',
        default=2,
        digits=(16, 3),
    )
    cfu_portion = fields.Float(
        string='CFU per portion',
        default=2,
        digits=(16, 3),
    )
    bacteria_gram_base = fields.Integer(
        string='Bacteria grams base',
        default=lambda rec: get_default(rec, 'aznut_calculator.powder_calculator_settings_main',
                                        'bacteria_gram_base'),
    )
    bacteria_gram_exponent = fields.Integer(
        string='Bacteria grams exponent',
        default=lambda rec: get_default(rec, 'aznut_calculator.powder_calculator_settings_main',
                                        'bacteria_gram_exponent'),
    )
    cfu_portion_uom = fields.Selection(
        selection=[('bn', 'BN'), ('m', 'M')],
        default='bn',
    )
    probiotic_portion = fields.Float(
        string='Probiotic per portion',
        compute='_compute_probiotic_portion',
        digits=(16, 2),
    )
    shipping = fields.Float(
        string='Shipping Cost',
        digits=(16, 2),
        compute='_compute_shipping',
        store=False
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='main_powder_calculator.currency_id',
    )
    taxes = fields.Float(
        string='Taxes',
        digits=(16, 2),
        default=lambda rec: get_default(rec, 'aznut_calculator.powder_calculator_settings_main',
                                        'taxes'),
    )
    jar_products_ids = fields.Many2many(
        'product.product',
        'jar_products_rel',
        compute='_compute_jar_products_ids',
    )
    box_product_id = fields.Many2one(
        'product.product',
        string='Box Product',
        domain=lambda rec: [
            ('categ_id', '=', rec.env.ref(
                'aznut_calculator.powder_calculator_settings_main').dog_treats_packaging_materials_category_id.id)],
    )
    shrink_product_id = fields.Many2one(
        'product.product',
        string='Shrink Product',
        domain=lambda rec: [
            ('categ_id', '=', rec.env.ref(
                'aznut_calculator.powder_calculator_settings_main').dog_treats_packaging_materials_category_id.id)],
    )
    ask_gpt_session_id = fields.Many2one(
        'ask.gpt.session',
        string='Session',
        compute='_compute_ask_gpt_session_id',
    )
    procurement_partner_id = fields.Many2one(
        'res.partner',
        default=lambda rec: get_default(rec, 'aznut_calculator.support_settings_main', 'procurement_partner_id'),
    )
    procurement_reply = fields.Html(
        string='Procurement Reply',
        compute="_compute_procurement_reply"
    )
    manufacturing_partner_id = fields.Many2one(
        'res.partner',
        default=lambda rec: get_default(rec, 'aznut_calculator.support_settings_main', 'manufacturing_partner_id'),
    )

    manufacturing_reply = fields.Html(
        string='Manufacturing Reply',
        compute="_compute_manufacturing_reply"
    )
    approval_partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        default=lambda rec: get_default(rec, 'aznut_calculator.support_settings_main', 'approval_partner_id'),
    )
    approval_email_sent = fields.Boolean(
        string='Approval Email Sent',
        copy=False,
    )
    is_calculator_salesperson = fields.Boolean(
        string='Is Calculator Salesperson',
        compute='_compute_is_calculator_salesperson',
    )

    @api.depends('product_id')
    def _compute_product_name(self):
        for calculator in self:
            calculator.product_name = calculator.product_id.name or 'No Product'

    @api.depends('manufacturing_partner_id')
    def _compute_manufacturing_reply(self):
        self.manufacturing_reply = CHAT_TEMPLATE % ''
        for powder_calculator in self:
            messages = self.env['mail.message'].sudo().search([
                ('res_id', '=', powder_calculator.id),
                ('model', '=', powder_calculator._name),
                ('author_id', '=', powder_calculator.manufacturing_partner_id.id),
                ('parent_id', '!=', False),
                ('message_type', '=', 'email')
            ])
            if messages:
                html = ''
                for message in messages:
                    html += f"""
                           <div class="mt-4" style="border-bottom:1px solid black;">
                               {message.body}
                               <p>{message.date.strftime("%d.%m.%Y %H:%M")}</p>
                           </div>
                           """
                powder_calculator.manufacturing_reply = Markup(CHAT_TEMPLATE % html)

    def _compute_is_calculator_salesperson(self):
        calculator_salesperson = self.env.user.has_group('aznut_calculator.group_calculator_salesperson')
        self.is_calculator_salesperson = calculator_salesperson

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, rec.product_name))
        return res

    @api.depends('procurement_partner_id')
    def _compute_procurement_reply(self):
        self.procurement_reply = CHAT_TEMPLATE % ''
        for powder_calculator in self:
            messages = self.env['mail.message'].sudo().search([
                ('res_id', '=', powder_calculator.id),
                ('model', '=', powder_calculator._name),
                ('author_id', '=', powder_calculator.procurement_partner_id.id),
                ('parent_id', '!=', False),
                ('message_type', '=', 'email')
            ])
            if messages:
                html = ''
                for message in messages:
                    html += f"""
                       <div class="mt-4" style="border-bottom:1px solid black;">
                           {message.body}
                           <p>{message.date.strftime("%d.%m.%Y %H:%M")}</p>
                       </div>
                       """
                powder_calculator.procurement_reply = Markup(CHAT_TEMPLATE % html)

    def _compute_ask_gpt_session_id(self):
        self.ask_gpt_session_id = False
        for product_calculator in self:
            product_calculator.ask_gpt_session_id = self.env['ask.gpt.session'].search([
                ('powder_calculator_id', '=', product_calculator.id),
            ], limit=1)

    def _compute_jar_products_ids(self):
        settings = self.env.ref('aznut_calculator.powder_calculator_settings_main')
        for calculator in self:
            calculator.jar_products_ids = settings.jar_products_ids

    def _compute_shipping(self):
        shipping_preset = self.env.ref('aznut_calculator.powder_calculator_settings_main').shipping_cost
        self.shipping = 0
        for powder_calculator in self:
            if powder_calculator.count_of_jars:
                total_bom_lb = sum(powder_calculator.active_ingredient_ids.mapped('total_bom_lb'))
                shipping = total_bom_lb * (shipping_preset / powder_calculator.count_of_jars)
                powder_calculator.shipping = round(shipping, 2)

    def _compute_probiotic_portion(self):
        self.probiotic_portion = False
        for powder_calculator in self:
            if powder_calculator.bacteria_gram and powder_calculator.cfu_portion and powder_calculator.bacteria_gram_base and powder_calculator.bacteria_gram_exponent:
                if powder_calculator.cfu_portion_uom == 'bn':
                    cfu_portion_calculated = powder_calculator.cfu_portion * 1000000000
                else:
                    cfu_portion_calculated = powder_calculator.cfu_portion * 1000000
                bacteria_gram_calculated = powder_calculator.bacteria_gram_base ** powder_calculator.bacteria_gram_exponent * powder_calculator.bacteria_gram
                powder_calculator.probiotic_portion = 1000 / (bacteria_gram_calculated / cfu_portion_calculated)

    def _compute_totals(self):
        for powder_calculator in self:
            total_ingredients_scoop_cost = sum(powder_calculator.mapped('active_ingredient_ids.cost_per_scoop'))
            active_in_jar = total_ingredients_scoop_cost * powder_calculator.ordered_jars_number
            ingredients_cost = active_in_jar
            jar_cost = sum([ingredients_cost, powder_calculator.shrink_price,
                            powder_calculator.label_price, powder_calculator.jar_price, powder_calculator.lid_price,
                            powder_calculator.shipping,
                            powder_calculator.box_price, powder_calculator.packaging_materials,
                            powder_calculator.taxes])
            powder_calculator.total_ingredients_scoop_cost = formatLang(self.env, total_ingredients_scoop_cost,
                                                                        currency_obj=powder_calculator.main_powder_calculator.currency_id,
                                                                        digits=4)
            powder_calculator.active_in_jar = active_in_jar
            powder_calculator.ingredients_cost = ingredients_cost
            powder_calculator.ready_jar_cost = jar_cost

    def _compute_price_per_jar(self):
        for powder_calculator in self:
            price_per_jar = sum(
                [powder_calculator.ready_jar_cost, powder_calculator.operating_expenses,
                 powder_calculator.profit]) - powder_calculator.discount_amount
            powder_calculator.price_per_jar = price_per_jar
            powder_calculator.total_price = price_per_jar * powder_calculator.count_of_jars

    def _compute_moq(self):
        for powder_calculator in self:
            powder_calculator.moq = powder_calculator._calculate_moq()

    def _compute_operating_expenses(self):
        for powder_calculator in self:
            if powder_calculator.jars_per_month:
                ratio = powder_calculator.monthly_exp / powder_calculator.jars_per_month
                powder_calculator.operating_expenses = ratio
            else:
                powder_calculator.operating_expenses = 0

    def _compute_jar_size(self):
        oz_uom = self.env.ref('uom.product_uom_oz')
        gr_uom = self.env.ref('uom.product_uom_gram')

        for powder_calculator in self:
            jar_size_gr = powder_calculator.scoop_grams * powder_calculator.ordered_jars_number
            jar_size_oz = gr_uom._compute_quantity(jar_size_gr, oz_uom, False, 'HALF-UP', False)
            powder_calculator.jar_size_gr = jar_size_gr
            powder_calculator.jar_size_oz = jar_size_oz

    def _compute_total_ingredients_bom_lb(self):
        oz_uom = self.env.ref('uom.product_uom_oz')
        gr_uom = self.env.ref('uom.product_uom_gram')
        lb_uom = self.env.ref('uom.product_uom_lb')
        for powder_calculator in self:
            quantity_gr = powder_calculator.jar_size_gr
            if powder_calculator.main_powder_calculator.use_active_multiply:
                quantity_gr *= 1.10
            quantity_oz = gr_uom._compute_quantity(quantity_gr, oz_uom, False, 'HALF-UP', False)
            quantity_oz *= powder_calculator.count_of_jars
            total_ingredients_bom_lb_theory = round(
                oz_uom._compute_quantity(quantity_oz, lb_uom, False, 'HALF-UP', False), 2)
            total_ingredients_bom_lb_actual = round(sum(powder_calculator.active_ingredient_ids.mapped('total_bom_lb')),
                                                    2)
            powder_calculator.verification_lb = compare_with_relative_tolerance(total_ingredients_bom_lb_theory,
                                                                                total_ingredients_bom_lb_actual)
            powder_calculator.total_ingredients_bom_lb_actual = total_ingredients_bom_lb_actual
            powder_calculator.total_ingredients_bom_lb_theory = total_ingredients_bom_lb_theory

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        rec = super(PowderCalculator, self).copy(default)
        for i in self.active_ingredient_ids:
            i.copy({'powder_calculator_id': rec.id})
        return rec

    def unlink(self):
        self.active_ingredient_ids.unlink()
        return super(PowderCalculator, self).unlink()

    def _get_order_details(self):
        order_details = self.read(order_details_fields)[0]
        names = self.fields_get(order_details_fields)
        prepared_details = []
        for val in names:
            if order_details[val] or val in ['jar_exist', 'lid_exist', 'label_exist']:
                if val == 'jar_size_oz':
                    text = '%s oz / %s g' % ('{:,.1f}'.format(self.jar_size_oz), '{:,.2f}'.format(self.jar_size_gr))
                    prepared_details.append({'val': text, 'name': 'Jar Weight'})
                elif val == 'scoop_grams':
                    text = '%s g' % '{:,.1f}'.format(order_details[val])
                    prepared_details.append({'val': text, 'name': names[val]['string']})
                elif val == 'jar_product_id':
                    prepared_details.append({'val': order_details[val][1], 'name': 'Jar Finish'})
                elif val == 'lid_product_id':
                    prepared_details.append({'val': order_details[val][1], 'name': 'Lid Finish'})
                else:
                    value = order_details[val]
                    if isinstance(value, int):
                        value = '{:,}'.format(value)
                    elif isinstance(value, float):
                        value = '{:,.2f}'.format(order_details[val])
                    prepared_details.append({'val': value, 'name': names[val]['string']})
        return sorted(prepared_details, key=lambda x: order_details_names.index(x['name']))

    def _get_row_quantity(self):
        order_details = self._get_order_details()
        active_ingredients = self.active_ingredient_ids
        return max(len(order_details), len(active_ingredients) + 1)

    def _get_cleaned_note(self):
        self.ensure_one()
        if not self.note:
            return self.note
        try:
            root = lxml_html.fragment_fromstring(self.note, create_parent='div')
        except Exception:
            return self.note

        return get_cleaned_note(root)

    def _calculate_moq(self):
        self.ensure_one()
        lb_uom = self.env.ref('uom.product_uom_lb')
        gr_uom = self.env.ref('uom.product_uom_gram')
        batch_gr = lb_uom._compute_quantity(900, gr_uom, False, 'HALF-UP', False)
        if self.jar_size_gr:
            return round(batch_gr / self.jar_size_gr, -2)
        return 0

    def write(self, vals):
        rec = super(PowderCalculator, self).write(vals)
        return rec

    @api.model
    def create(self, vals):
        res = super().create(vals)
        return res


class PowderActiveIngredient(models.Model):
    _name = 'powder.active.ingredient'
    _description = 'Powder Active Ingredient'

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        domain=lambda rec: ['&', ('uom_id', '=', rec.env.ref('uom.product_uom_lb').id), '|',
                            ('calculator_uom_id', '=', rec.env.ref('aznut_calculator.product_uom_mg').id),
                            ('calculator_uom_id', '=', rec.env.ref('uom.product_uom_gram').id)],
    )
    quantity = fields.Float(
        string='Quantity',
        digits=(16, 4),
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit',
        related='product_id.calculator_uom_id',
    )
    powder_calculator_id = fields.Many2one(
        'powder.calculator',
        'Powder Calculator',
    )
    ordered_jars_number = fields.Integer(
        related='powder_calculator_id.ordered_jars_number',
        digits=(16, 2),
    )
    total_bom_lb = fields.Float(
        string='Total BoM Lb',
        compute='_compute_total_bom_lb',
        digits=(16, 4),
    )
    cost_per_lb = fields.Float(
        string='Cost per Lb',
        store=True,
        compute='_compute_cost_per_lb',
        readonly=True,
        digits=(16, 2),
    )
    cost_per_scoop = fields.Float(
        string='Invisible Cost per Scoop',
        compute='_compute_others_costs',
        digits=(16, 4),
    )
    display_cost_per_scoop = fields.Char(
        string='Cost per Scoop',
        compute='_compute_others_costs',
        digits=(16, 4),
    )
    color = fields.Selection(
        [('blue', 'Blue'), ('red', 'Red'), ('yellow', 'Yellow'), ('green', 'Green')],
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='powder_calculator_id.main_powder_calculator.currency_id',
    )
    mg_quantity = fields.Float(
        string='Mg Quantity',
        digits=(16, 4),
        compute='_compute_mg_quantity',
    )
    forecast_availability = fields.Float(
        string='Forecast Availability',
        compute='_compute_forecast_information',
        digits=(16, 16),
        compute_sudo=True,
    )
    lb_uom_id = fields.Many2one(
        'uom.uom',
        default=lambda self: self.env.ref('uom.product_uom_lb').id,
    )
    seq_number = fields.Integer(
        string='No.',
        compute='_compute_seq_number',
    )
    free_qty = fields.Float(
        related='product_id.free_qty',
        string='Free Stock Quantity',
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        related='product_id.uom_id',
        string='Free Stock UoM',
    )
    sequence = fields.Integer(
        string="Sequence",
        default=1,
    )

    def _compute_seq_number(self):
        calculate_seq_number(self)

    @api.depends('quantity')
    def _compute_forecast_information(self):
        for ingredient in self:
            uom_from = ingredient.product_id.uom_id
            uom_to = ingredient.uom_id
            quantity = uom_to._compute_quantity(ingredient.quantity, uom_from, False, 'HALF-UP', False)
            ingredient.forecast_availability = ingredient.product_id.qty_available - quantity

    @api.depends('quantity', 'uom_id')
    def _compute_mg_quantity(self):
        mg_uom = self.env.ref('aznut_calculator.product_uom_mg')
        for active_ingredient in self:
            uom = active_ingredient.uom_id
            active_ingredient.mg_quantity = uom._compute_quantity(active_ingredient.quantity, mg_uom, False, 'HALF-UP',
                                                                  False)

    def _compute_total_bom_lb(self):
        mg_uom = self.env.ref('aznut_calculator.product_uom_mg')
        lb_uom = self.env.ref('uom.product_uom_lb')
        kg_uom = self.env.ref('uom.product_uom_kgm')
        for active_ingredient in self:
            quantity_mg = active_ingredient.mg_quantity
            if active_ingredient.powder_calculator_id.main_powder_calculator.use_active_multiply:
                quantity_mg *= 1.10
            total_bom_mg = quantity_mg * active_ingredient.ordered_jars_number
            total_bom_kg = mg_uom._compute_quantity(total_bom_mg, kg_uom, False, 'HALF-UP',
                                                    False) * active_ingredient.powder_calculator_id.count_of_jars
            total_bom_lb = kg_uom._compute_quantity(total_bom_kg, lb_uom, False, 'HALF-UP', False)
            active_ingredient.total_bom_lb = total_bom_lb

    @api.depends('product_id')
    def _compute_cost_per_lb(self):
        for active_ingredient in self:
            active_ingredient.cost_per_lb = active_ingredient.product_id.standard_price

    def _compute_others_costs(self):
        for active_ingredient in self:
            currency = active_ingredient.currency_id
            mg_quantity = active_ingredient.mg_quantity
            cost_per_kg = active_ingredient.cost_per_lb * 2.20462
            cost_per_scoop = (cost_per_kg / 1000000) * mg_quantity
            if active_ingredient.powder_calculator_id.main_powder_calculator.use_active_multiply:
                cost_per_scoop *= 1.10
            active_ingredient.cost_per_scoop = cost_per_scoop
            active_ingredient.display_cost_per_scoop = formatLang(self.env, cost_per_scoop, currency_obj=currency,
                                                                  digits=4)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        rec = super(PowderActiveIngredient, self).copy(default)
        rec.write({'cost_per_lb': self.cost_per_lb})
        return rec
