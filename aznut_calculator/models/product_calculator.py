################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2019 SmartTek (<https://smartteksas.com/>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
################################################################################

from odoo import fields, models, api, Command
from odoo.exceptions import ValidationError
from odoo.osv.expression import AND
from werkzeug.urls import url_join

from markupsafe import Markup
from re import search
from lxml import html as lxml_html
from datetime import timedelta

from .ask_gpt import get_gpt_session_window, CHAT_TEMPLATE, remove_emojis

order_details_fields = ['flavour_ids', 'count_of_jars', 'jar_exist', 'lid_exist', 'label_exist', 'jar_product_id',
                        'lid_product_id', 'label_finish', 'chews_per_jar',
                        'chew_size', 'portion_grams', 'jar_weight',
                        'shape_ids']

order_details_names = ['Flavour', 'Count of Jars', 'Jar', 'Lid', 'Label',
                       'Jar Finish', 'Lid Finish', 'Label Finish', 'Approximate Chews',
                       'Each Chew Size', 'Serving Size (Total gr.)', 'Jar size',
                       'Shape']
po_state_order = ['done', 'purchase', 'to approve', 'sent', 'draft', 'cancel']

TABLE_TEMPLATE = """
<h3>%s</h3>
<table class="table table-bordered">
    <thead>
      %s
    </thead>
    <tbody>
        %s
    </tbody>
</table>
"""

TOTAL_TABLE_TEMPLATE = """
<div class="d-flex mt-3">
    <div style="width:40%">
    </div>
    <div style="width: 50%;margin-left: 10%;">
        <table class="w-100">
            <tbody>
              {}
            </tbody>
        </table>
    </div>
</div>
"""


def calculator_salesperson_search(self, args):
    if self.env.user.has_group('aznut_calculator.group_calculator_salesperson'):
        args += [('create_uid', '=', self.env.user.id)]
    return args


def calculator_salesperson_read_group(self, domain):
    if self.env.user.has_group('aznut_calculator.group_calculator_salesperson'):
        domain = AND([domain, [('create_uid', '=', self.env.user.id)]])
    return domain


def send_approval_mail(calculators, model='main.product.calculator'):
    for child_calculator in calculators.filtered(lambda rec: rec.approval_partner_id):
        body = calculators.env.ref('aznut_calculator.support_settings_main').approval_text
        partner = calculators.env.ref('aznut_calculator.support_settings_main').sudo().approval_partner_id
        if model == 'main.product.calculator':
            main_calculator = calculators.env[model].search([
                ('calculator_ids', 'in', child_calculator.ids)
            ], limit=1)
        else:
            main_calculator = child_calculator.main_powder_calculator
        if main_calculator:
            if '%name%' in body:
                body = body.replace('%name%', partner.name or '')
            if '%calculator_name%' in body:
                body = body.replace('%calculator_name%', child_calculator.product_name or '')
            if '%link%' in body:
                base_url = child_calculator.get_base_url()
                if model == 'main.product.calculator':
                    menu_id = calculators.env.ref('aznut_calculator.menu_product_calculators').id
                    action_id = calculators.env.ref('aznut_calculator.action_main_product_calculator_tree').id
                    secondary_url = 'web#id=%s&menu_id=%s&action=%s&model=%s&view_type=form' % (
                        main_calculator.id, menu_id, action_id, model
                    )
                else:
                    menu_id = calculators.env.ref('aznut_calculator.menu_powder_calculator_tree').id
                    action_id = calculators.env.ref('aznut_calculator.action_main_powder_calculator_tree').id
                    secondary_url = 'web#id=%s&menu_id=%s&action=%s&model=%s&view_type=form' % (
                        main_calculator.id, menu_id, action_id, model
                    )
                link = url_join(base_url, secondary_url)
                body = body.replace('%link%', link)
            calculators.env['mail.compose.message'].create({
                'body': body,
                'subject': 'Request For Calculator Approval',
                'partner_ids': partner.ids,
                'res_id': main_calculator.id,
                'model': model,
            }).action_send_mail()
            child_calculator.update({'approval_email_sent': True})


def get_quantity_from_ingredient(ingredient, quantity_field):
    quantity = getattr(ingredient, quantity_field)
    if ingredient._name == 'active.ingredient':
        moq = ingredient.calculator_id.moq
        if moq:
            count_of_jars = ingredient.calculator_id.count_of_jars
            return quantity * (count_of_jars / moq)
    return quantity


def get_default(instance, ref, field):
    record = instance.env.ref(ref, raise_if_not_found=False)
    if not instance._context.get('module') and record and hasattr(record, field):
        return getattr(record, field)
    return False


def custom_round(value):
    integer_part = int(value)
    fractional_part = abs(value - integer_part)
    if fractional_part == 0:
        return integer_part
    if fractional_part >= 0.5:
        if fractional_part > 0.5:
            return integer_part + 1 if value > 0 else integer_part - 1
        else:
            return integer_part + 0.5 if value > 0 else integer_part - 0.5
    else:
        return integer_part + 0.5 if value > 0 else integer_part - 0.5


def check_ingredients_is_unique(fields_to_check, rec):
    msg = []
    for key, field in fields_to_check.items():
        ingredients = list(map(lambda record: record.product_id, rec.mapped('%s' % field)))
        ingredients_duplicates = [product.name for product in ingredients if
                                  ingredients.count(product) > 1 and product.name]
        if ingredients_duplicates:
            msg.append('%s ingredients must be unique: %s' % (key, ', '.join(set(ingredients_duplicates))))
    return msg


def get_ingredients_table(ingredients, product_field, quantity_field, uom_field, vendors=False, ing_type='active'):
    if not ingredients:
        return ''

    ing_fields = ingredients._fields
    if not all(field in ing_fields for field in [product_field, quantity_field, uom_field]):
        return ''

    name = 'Base Ingredients' if ing_type == 'base' else 'Active Ingredients'

    th_list = ['<th>Product</th>', '<th>Quantity</th>', '<th>UoM</th>']
    if vendors:
        th_list += ['<th>Last PO#</th>', '<th>Vendors</th>']
    th_string = ''.join(th_list)

    tbody_rows = []
    for ingredient in ingredients:
        product = getattr(ingredient, product_field, None)
        uom = getattr(ingredient, uom_field, None)
        quantity = get_quantity_from_ingredient(ingredient, quantity_field)

        row_cells = [
            f"<td>{remove_emojis(product.name) if product else 'No Name'}</td>",
            f"<td>{quantity:.4f}</td>",
            f"<td>{uom.name if uom else '&nbsp;'}</td>"
        ]

        if vendors:
            po_lines = ingredient.product_id.purchase_order_line_ids if ingredient.product_id else []
            latest_po_line = sorted(
                po_lines,
                key=lambda line: (
                    po_state_order.index(line.state) if line.state in po_state_order else len(po_state_order),
                    -line.id
                )
            )[:1]
            last_po = latest_po_line[0].order_id.name if latest_po_line else '&nbsp;'
            vendors_str = ', '.join(ingredient.product_id.seller_ids.mapped('name.name')) if ingredient.product_id else '&nbsp;'
            row_cells += [f"<td>{last_po}</td>", f"<td>{vendors_str}</td>"]

        tbody_rows.append(f"<tr>{''.join(row_cells)}</tr>")

    return TABLE_TEMPLATE % (name, f"<tr>{th_string}</tr>", ''.join(tbody_rows))


def generate_total_table(names_list, values_list):
    composite_string = ''
    for i in range(0, len(names_list)):
        composite_string += """
        <tr style="line-height: 3;border-top: 1px solid black;">
            <td>%s:</td>
            <td style="text-align: right;">
            %s
            </td>
        </tr>
        """ % (names_list[i], values_list[i])
    if composite_string:
        return TOTAL_TABLE_TEMPLATE.format(composite_string)
    return ''


def get_mail_action(child_culculator, main_calc_name, body, partner_id, vendors_ingredients=False):
    res = child_culculator.env['mail.compose.message'].create({
        'model': child_culculator._name,
        'res_id': child_culculator.id,
        'composition_mode': 'comment',
        'body': body,
        'subject': '%s / %s' % (main_calc_name, child_culculator.display_name),
        'partner_ids': partner_id.ids,
    })
    ctx = {
        'mark_as_sent': True,
        'custom_layout': "mail.mail_notification_light",
        'force_email': True,
    }
    if vendors_ingredients:
        ctx.update({'ing_ids': vendors_ingredients.ids, 'ing_model': vendors_ingredients[:1]._name})
    return {
        'type': 'ir.actions.act_window',
        'view_mode': 'form',
        'res_model': 'mail.compose.message',
        'views': [(False, 'form')],
        'view_id': False,
        'res_id': res.id,
        'target': 'new',
        'context': ctx,
    }


def get_cleaned_note(root):
    def is_visually_empty(el):
        text = ''.join(el.itertext()).replace('\xa0', '').replace('\n', '').strip()
        return not text

    def recursive_clean(el):
        for child in list(el):
            recursive_clean(child)
        if is_visually_empty(el) and not el.attrib.get('src'):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    recursive_clean(root)
    if is_visually_empty(root):
        return ""
    return lxml_html.tostring(root, encoding='unicode', method='html')


def calculate_seq_number(records):
    def get_id(ing):
        use_origin = not isinstance(ing.id, int)
        return ing.id.origin or int(search(r'\d+', ing.id.ref).group()) if use_origin else ing.id

    sorted_ingredients = sorted(records, key=lambda ing: (ing.sequence, get_id(ing)))
    sorted_ids = [get_id(ing) for ing in sorted_ingredients]

    for ingredient in records:
        ing_id = get_id(ingredient)
        try:
            ingredient.seq_number = sorted_ids.index(ing_id) + 1
        except ValueError:
            ingredient.seq_number = False


class MainProductCalculator(models.Model):
    _name = 'main.product.calculator'
    _description = 'Main Chews Calculator'
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
    calculator_ids = fields.Many2many(
        'product.calculator',
        string='Calculators',
        readonly=True,
        copy=False,
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
        default='draft'
    )
    custom_calculator_id = fields.Many2one(
        'product.calculator',
        string='Custom Chews Calculator'
    )
    active_calculator_id = fields.Many2one(
        'product.calculator',
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
        default=lambda self: self.env.user.id
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.user.company_id.currency_id
    )

    # child calculators
    portion_grams = fields.Float(
        related='active_calculator_id.portion_grams',
        store=True,
        readonly=False
    )
    one_batch_lb = fields.Float(
        related='active_calculator_id.one_batch_lb',
    )
    jar_weight = fields.Float(
        related='active_calculator_id.jar_weight',
        store=True,
        readonly=False,
    )
    ready_jar_cost = fields.Float(
        related='active_calculator_id.ready_jar_cost',
    )
    active_cost = fields.Float(
        related='active_calculator_id.active_cost'
    )
    base_cost = fields.Float(
        related='active_calculator_id.base_cost',
    )
    total_cost = fields.Float(
        related='active_calculator_id.total_cost'
    )
    jar_price = fields.Float(
        related='active_calculator_id.jar_price',
        store=True,
        readonly=False,
    )
    lid_price = fields.Float(
        related='active_calculator_id.lid_price',
        store=True,
        readonly=False,
    )
    box_price = fields.Float(
        related='active_calculator_id.box_price',
        store=True,
        readonly=False,
    )
    label_price = fields.Float(
        related='active_calculator_id.label_price',
        store=True,
        readonly=False,
    )
    shrink_price = fields.Float(
        related='active_calculator_id.shrink_price',
        store=True,
        readonly=False,
    )
    operating_expenses = fields.Float(
        related='active_calculator_id.operating_expenses',
    )
    monthly_exp = fields.Integer(
        related='active_calculator_id.monthly_exp',
        store=True,
        readonly=False,
    )
    jars_per_month = fields.Integer(
        related='active_calculator_id.jars_per_month',
        store=True,
        readonly=False,
    )
    bacteria_gram = fields.Float(
        related='active_calculator_id.bacteria_gram',
        store=True,
        readonly=False,
    )
    cfu_portion = fields.Float(
        related='active_calculator_id.cfu_portion',
        store=True,
        readonly=False,
    )
    probiotic_portion = fields.Float(
        related='active_calculator_id.probiotic_portion',
    )
    active_ingredient_ids = fields.Many2many(
        related='active_calculator_id.active_ingredient_ids',
        readonly=False,
        inverse='_inverse_active_ingredient_ids',
    )
    readonly_active_ingredient_ids = fields.Many2many(
        related='active_calculator_id.readonly_active_ingredient_ids',
    )
    base_ingredient_ids = fields.Many2many(
        related='active_calculator_id.base_ingredient_ids',
        readonly=False,
        inverse='_inverse_base_ingredient_ids',
    )
    base_ingredients_total_cost = fields.Float(
        related='active_calculator_id.base_ingredients_total_cost',
    )
    base_ingredients_total_quantity = fields.Float(
        related='active_calculator_id.base_ingredients_total_quantity',
    )
    base_ingredients_total_quantity_percent = fields.Float(
        related='active_calculator_id.base_ingredients_total_quantity_percent',
    )
    base_ingredients_total_quantity_diff = fields.Float(
        related='active_calculator_id.base_ingredients_total_quantity_diff',
    )

    readonly_active_ingredients_total_cost = fields.Float(
        related='active_calculator_id.readonly_active_ingredients_total_cost',

    )
    readonly_active_ingredients_total_quantity = fields.Float(
        related='active_calculator_id.readonly_active_ingredients_total_quantity',
    )

    readonly_active_ingredients_total_quantity_diff = fields.Float(
        related='active_calculator_id.readonly_active_ingredients_total_quantity_diff',
    )
    bom_count = fields.Integer(
        string='BoM Count',
        compute='_compute_bom_count',
    )

    cfu_portion_uom = fields.Selection(
        related='active_calculator_id.cfu_portion_uom',
        store=True,
        readonly=False,
    )
    bacteria_gram_base = fields.Integer(
        related='active_calculator_id.bacteria_gram_base',
    )
    bacteria_gram_exponent = fields.Integer(
        related='active_calculator_id.bacteria_gram_exponent',
    )
    label_exist = fields.Boolean(
        related='active_calculator_id.label_exist',
        store=True,
        readonly=False,
    )
    label_finish = fields.Selection(
        related='active_calculator_id.label_finish',
        store=True,
        readonly=False,
    )
    jar_exist = fields.Boolean(
        related='active_calculator_id.jar_exist',
        store=True,
        readonly=False,
    )
    jar_product_id = fields.Many2one(
        related='active_calculator_id.jar_product_id',
        store=True,
        readonly=False,
    )
    lid_exist = fields.Boolean(
        related='active_calculator_id.lid_exist',
        store=True,
        readonly=False,
    )
    lid_product_id = fields.Many2one(
        related='active_calculator_id.lid_product_id',
        store=True,
        readonly=False,
    )
    chews_per_jar = fields.Integer(
        related='active_calculator_id.chews_per_jar',
        store=True,
        readonly=False,
    )
    chew_size = fields.Float(
        related='active_calculator_id.chew_size',
        store=True,
        readonly=False,
    )
    moq = fields.Float(
        related='active_calculator_id.moq',
    )
    count_of_jars = fields.Integer(
        related='active_calculator_id.count_of_jars',
        store=True,
        readonly=False,
    )
    flavour_ids = fields.Many2many(
        related='active_calculator_id.flavour_ids',
        inverse='_inverse_flavour_ids',
        readonly=False,
    )
    total_price = fields.Float(
        related='active_calculator_id.total_price',
    )
    lead_time = fields.Text(
        related='active_calculator_id.lead_time',
    )
    discount_amount = fields.Float(
        related='active_calculator_id.discount_amount',
        store=True,
        readonly=False,
    )
    profit = fields.Float(
        related='active_calculator_id.profit',
        store=True,
        readonly=False,
    )
    shipping = fields.Float(
        related='active_calculator_id.shipping',
    )
    note = fields.Html(
        related='active_calculator_id.note',
        store=True,
        readonly=False,
    )
    product_name = fields.Char(
        related='active_calculator_id.product_name',
    )
    report_base_ingredients = fields.Char(
        related='active_calculator_id.report_base_ingredients',
        store=True,
        readonly=False,
    )
    is_calculator_administrator = fields.Boolean(
        related='active_calculator_id.is_calculator_administrator',
    )
    is_calculator_manager = fields.Boolean(
        related='active_calculator_id.is_calculator_manager',
    )
    is_calculator_salesperson = fields.Boolean(
        string='Is Calculator Salesperson',
        compute='_compute_is_calculator_salesperson',
    )
    active_ingredients_total_quantity = fields.Float(
        related='active_calculator_id.active_ingredients_total_quantity'
    )
    shape_ids = fields.Many2many(
        related='active_calculator_id.shape_ids',
        inverse='_inverse_shape_ids',
        readonly=False,
    )
    net_cost = fields.Float(
        string='Net Cost',
        related='active_calculator_id.net_cost'
    )
    use_manual_report_base = fields.Boolean(
        string="Report Custom Base Ingredietns"
    )
    manual_report_base_ingredients = fields.Char(
        string="Custom Base Ingredients List:"
    )
    readonly_active_ingredients_total_quantity_percent = fields.Float(
        related='active_calculator_id.readonly_active_ingredients_total_quantity_percent',
    )
    taxes = fields.Float(
        related='active_calculator_id.taxes',
        store=True,
        readonly=False,
    )
    jar_products_ids = fields.Many2many(
        'product.product',
        related='active_calculator_id.jar_products_ids',
    )
    box_product_id = fields.Many2one(
        related='active_calculator_id.box_product_id',
        store=True,
        readonly=False,
    )
    shrink_product_id = fields.Many2one(
        related='active_calculator_id.shrink_product_id',
        store=True,
        readonly=False,
    )
    ask_gpt_session_id = fields.Many2one(
        related='active_calculator_id.ask_gpt_session_id',
    )
    procurement_partner_id = fields.Many2one(
        related='active_calculator_id.procurement_partner_id',
        store=True,
        readonly=False,
    )
    procurement_reply = fields.Html(
        related='active_calculator_id.procurement_reply',
    )
    is_user_calculator_procurement = fields.Boolean(
        related='active_calculator_id.is_user_calculator_procurement',
    )
    manufacturing_partner_id = fields.Many2one(
        related='active_calculator_id.manufacturing_partner_id',
        store=True,
        readonly=False,
    )
    manufacturing_reply = fields.Html(
        related='active_calculator_id.manufacturing_reply',
    )
    calculator_product_category_id = fields.Many2one(
        'product.category',
        string='Calculator Product Category',
        default=lambda rec: get_default(rec, 'aznut_calculator.product_calculator_settings_main',
                                        'calculator_product_category_id'),
    )
    approval_partner_id = fields.Many2one(
        'res.partner',
        related='active_calculator_id.approval_partner_id',
    )
    approval_email_sent = fields.Boolean(
        related='active_calculator_id.approval_email_sent',
    )
    show_approval_button = fields.Boolean(
        string='Show Approval Button',
        compute='_compute_show_approval_button',
    )
    allowed_calculators_ids = fields.Many2many(
        'product.calculator',
        'allowed_calculators_rel',
        compute='_compute_allowed_calculators_ids',
    )

    @api.onchange('shrink_product_id')
    def _onchange_shrink_product_id(self):
        self.shrink_price = self.shrink_product_id.standard_price

    @api.onchange('box_product_id')
    def _onchange_box_product_id(self):
        self.box_price = self.box_product_id.standard_price * (self.box_product_id.calculator_uom_id.ratio or 1)

    @api.onchange('use_manual_report_base')
    def _onchange_use_manual_report_base(self):
        if self.active_calculator_id and not self.manual_report_base_ingredients:
            self.manual_report_base_ingredients = self.active_calculator_id.report_base_ingredients

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.lead_id.partner_id = self.partner_id

    @api.depends('calculator_ids')
    def _compute_allowed_calculators_ids(self):
        for main_calculator in self:
            allowed_calculators_ids = main_calculator.calculator_ids
            if main_calculator.is_calculator_salesperson:
                allowed_calculators_ids = allowed_calculators_ids.filtered(
                    lambda calculator: calculator.create_uid.id == self.env.user.id)
            main_calculator.allowed_calculators_ids = allowed_calculators_ids

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

    @api.depends('partner_id')
    def _compute_allowed_partners(self):
        calculator_manager = self.env.user.has_group('aznut_calculator.group_calculator_manager')
        for rec in self:
            if calculator_manager:
                rec.allowed_partner_ids = self.env['res.partner'].search([])
            else:
                rec.allowed_partner_ids = [self.env.user.partner_id.id]

    def _compute_bom_count(self):
        for rec in self:
            rec.bom_count = self.env['mrp.bom'].search_count([('product_calculator_id', 'in', rec.calculator_ids.ids)])

    @api.onchange('label_exist', 'jar_exist', 'lid_exist')
    def _onchange_label_or_jar_lid(self):
        if not self.label_exist:
            self.label_finish = False
        if not self.jar_exist:
            self.jar_product_id = False
        if not self.lid_exist:
            self.lid_product_id = False

    @api.onchange('chews_per_jar', 'chew_size')
    def _onchange_jar_weight(self):
        self.jar_weight = 0
        for rec in self:
            jar_weight = rec.chews_per_jar * rec.chew_size * 0.035274
            rec.jar_weight = custom_round(jar_weight)

    @api.onchange('jar_product_id')
    def _onchange_jar_product(self):
        self.jar_price = self.jar_product_id.standard_price

    @api.onchange('lid_product_id')
    def _onchange_lid_product(self):
        self.lid_price = self.lid_product_id.standard_price

    @api.onchange('label_exist')
    def _onchange_label_exist(self):
        label_preset = self.env.ref('aznut_calculator.product_calculator_settings_main').label_preset
        for rec in self:
            rec.label_price = label_preset if rec.label_exist else 0

    @api.onchange('active_ingredient_ids')
    def _onchange_active_ingredient_ids(self):
        self.active_ingredient_ids._compute_seq_number()

    @api.onchange('base_ingredient_ids')
    def _onchange_base_ingredient_ids(self):
        self.base_ingredient_ids._compute_seq_number()

    def _inverse_base_ingredient_ids(self):
        for main_calculator in self:
            main_calculator.active_calculator_id.base_ingredient_ids = main_calculator.base_ingredient_ids

    def _inverse_active_ingredient_ids(self):
        for main_calculator in self:
            main_calculator.active_calculator_id.active_ingredient_ids = main_calculator.active_ingredient_ids

    def _inverse_flavour_ids(self):
        for main_calculator in self:
            main_calculator.active_calculator_id.flavour_ids = main_calculator.flavour_ids

    def _inverse_shape_ids(self):
        for main_calculator in self:
            main_calculator.active_calculator_id.shape_ids = main_calculator.shape_ids

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if not kwargs.get('partner_ids') and kwargs.get(
                'subtype_xmlid') != 'mail.mt_comment' and not self.env.context.get('activity_mail'):
            raise ValidationError('Partner email is not set')
        if self.env.context.get('mark_as_sent'):
            if self.lead_id:
                self.lead_id.message_post(body=kwargs.get('body'), attachment_ids=kwargs.get('attachment_ids'))
            self.state = 'sent'
        return super(MainProductCalculator, self.with_context(
            mail_post_autofollow=self.env.context.get('mail_post_autofollow', True))).message_post(**kwargs)

    def create_opportunity(self):
        self.ensure_one()
        lead = self.sudo().lead_id
        if not lead:
            created_lead = self.env['crm.lead'].sudo().create({
                'name': self.display_name,
                'user_id': self.user_id.id,
                'partner_id': self.partner_id.id,
                'type': 'opportunity',
                'main_product_calculator_id': self.id,
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
            'domain': [('product_calculator_id', 'in', self.calculator_ids.ids)],
            'context': {'create': 0},
        }

    def create_bom(self):
        main_wizard = self.env['product.calculator.create.bom.wizard'].create({})
        self.ensure_one()
        suitable_wizard_calculators = []
        for calculator in self.calculator_ids.filtered(lambda rec: not rec.result_product_tmpl_id):
            create_bom_wizard_lines_ids = []
            for readonly_active_ingredient in calculator.readonly_active_ingredient_ids:
                create_bom_wizard_lines_ids.append(self.env['create.bom.wizard.line'].create({
                    'product_id': readonly_active_ingredient.product_id.id,
                    'quantity': readonly_active_ingredient.readonly_quantity,
                    'uom_id': readonly_active_ingredient.uom_id.id,
                }).id)
            for base_ingredient in calculator.base_ingredient_ids:
                create_bom_wizard_lines_ids.append(self.env['create.bom.wizard.line'].create({
                    'product_id': base_ingredient.product_id.id,
                    'quantity': base_ingredient.quantity,
                    'uom_id': base_ingredient.uom_id.id,
                }).id)
            wizard_calculator = self.env['create.bom.wizard.product'].create({
                'create_bom_wizard_lines_ids': create_bom_wizard_lines_ids,
                'quantity': calculator.moq,
                'calculator_id': calculator.id,
                'main_wizard_id': main_wizard.id,
            })
            suitable_wizard_calculators.append(wizard_calculator.id)
        view_id = self.env.ref('aznut_calculator.product_calculator_create_bom_wizard_form_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create BoM',
            'view_mode': 'form',
            'res_model': 'product.calculator.create.bom.wizard',
            'target': 'new',
            'view_id': view_id,
            'res_id': main_wizard.id,
        }

    def send_by_email(self):
        self.ensure_one()
        template_id = self.env['ir.model.data']._xmlid_to_res_id('aznut_calculator.main_product_calculator_email',
                                                                 raise_if_not_found=False)
        template = self.env['mail.template'].browse(template_id)
        if template.lang:
            lang = template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'main.product.calculator',
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

    def copy_child_calculator(self):
        self.ensure_one()
        view_id = self.env.ref('aznut_calculator.copy_product_calculator_wizard_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Copy Child Calculator',
            'view_mode': 'form',
            'res_model': 'copy.product.calculator.wizard',
            'target': 'new',
            'view_id': view_id,
            'context': {
                'default_main_calculator_id': self.id,
                'default_calculator_id': self.active_calculator_id.id,
            }
        }

    def _get_expiry_date(self):
        self.ensure_one()
        return self.create_date + timedelta(days=15)

    @api.model
    def create(self, vals):
        if 'name' not in vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('product.calculator') or 'New'
        rec = super(MainProductCalculator, self).create(vals)
        rec._update_calculators()
        lead_id = vals.get('lead_id', False)
        if lead_id:
            lead = self.env['crm.lead'].sudo().browse(lead_id).exists()
            lead.main_product_calculator_id = rec.id
        return rec

    def write(self, values):
        rec = super(MainProductCalculator, self).write(values)
        self._update_calculators()
        return rec

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        return super(MainProductCalculator, self)._search(calculator_salesperson_search(self, args), offset, limit,
                                                          order, count, access_rights_uid)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        return super(MainProductCalculator, self).read_group(calculator_salesperson_read_group(self, domain), fields,
                                                             groupby, offset=offset, limit=limit,
                                                             orderby=orderby, lazy=lazy)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        rec = super(MainProductCalculator, self).copy(default)
        products = self.products_ids
        calculators = self.env['product.calculator'].browse([i.copy().id for i in self.calculator_ids])
        custom_calculator = calculators.filtered(lambda c: c.calculator_type == 'custom')[:1]
        vals = {
            'calculator_ids': calculators,
            'products_ids': products.ids,
        }
        if custom_calculator:
            vals.update({
                'custom_calculator_id': custom_calculator.id,
            })
        rec.write(vals)
        return rec

    def manage_custom_calculator(self):
        self.ensure_one()
        if self._context.get('create_custom_calculator') and not self.custom_calculator_id:
            custom_calculator_id = self.env['product.calculator'].create({
                'calculator_type': 'custom',
            })
            self.write({
                'custom_calculator_id': custom_calculator_id,
                'calculator_ids': [(4, custom_calculator_id.id)],
            })
        elif self._context.get('delete_custom_calculator') and self.custom_calculator_id:
            self.custom_calculator_id.unlink()

    def _update_calculators(self):
        for main_calculator in self:
            existing_calculators = self.env['product.calculator']
            for product in main_calculator.products_ids:
                existing_calculator = main_calculator.calculator_ids.filtered(
                    lambda c: c.calculator_type == 'product' and c.product_id == product)[:1]
                if not existing_calculator:
                    existing_calculator = self.env['product.calculator'].create({
                        'product_id': product.id,
                        'calculator_type': 'product'
                    })
                    bom_id = product.bom_ids[:1]
                    if bom_id:
                        existing_calculator.write({
                            'active_ingredient_ids': [(0, 0, {
                                'product_id': bom_line.product_id.id,
                                'quantity': bom_line.product_qty,
                                'calculator_id': existing_calculator.id,
                            }) for bom_line in bom_id.bom_line_ids]
                        })
                    main_calculator.calculator_ids = [(4, existing_calculator.id)]
                existing_calculators = existing_calculators | existing_calculator
            calculators_to_delete = main_calculator.calculator_ids.filtered(
                lambda c: c.calculator_type == 'product') - existing_calculators
            if calculators_to_delete:
                calculators_to_delete.unlink()

    def unlink(self):
        self.calculator_ids.unlink()
        return super(MainProductCalculator, self).unlink()

    def action_add_moq_discount(self):
        if self.moq:
            moq_dividers = self.env['product.calculator.moq.discount'].search([])
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

    def action_approve_calculator(self):
        self.mapped('active_calculator_id').write({
            'approval_email_sent': False,
        })

    def action_open_compare_wizard(self):
        self.ensure_one()
        view = self.env.ref('aznut_calculator.product_compare_calculator_wizard_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Compare Chews Calculators',
            'view_mode': 'form',
            'res_model': 'product.compare.calculator.wizard',
            'target': 'new',
            'view_id': view.id,
            'context': {
                'default_main_calculator_id': self.id,
                'default_calculator_first': self.active_calculator_id.id,
            }
        }

    def action_open_calculators_costs(self):
        self.ensure_one()
        view = self.env.ref('aznut_calculator.product_calculator_tree_view')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Calculators Costs',
            'view_mode': 'tree',
            'res_model': 'product.calculator',
            'target': 'new',
            'domain': [('id', 'in', self.calculator_ids.ids)],
            'view_id': view.id,
        }

    def action_generate_ask_gpt_session(self):
        self.ensure_one()
        if not self.ask_gpt_session_id:
            self.env['ask.gpt.session'].sudo().create({
                'product_calculator_id': self.active_calculator_id.id,
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
            tables = [
                get_ingredients_table(self.active_ingredient_ids.filtered(lambda ing: ing.forecast_availability < 0),
                                      'product_id', 'readonly_quantity', 'uom_id', vendors=True, ing_type='active'),
            ]
            body = body.replace('%ingredients%', Markup(''.join(filter(None, tables))))

        return get_mail_action(self.active_calculator_id, self.display_name, body, self.procurement_partner_id,
                               self.active_ingredient_ids.filtered(lambda ing: ing.forecast_availability < 0))

    def action_send_approval_mail(self):
        send_approval_mail(self.mapped('active_calculator_id'), 'main.product.calculator')

    def action_send_manufacturing_mail(self):
        self.ensure_one()
        body = self.env.ref('aznut_calculator.support_settings_main').manufacturing_text
        if '%name%' in body:
            body = body.replace('%name%', self.manufacturing_partner_id.name or '')
        if '%ingredients%' in body:
            tables = [
                get_ingredients_table(self.base_ingredient_ids, 'product_id', 'quantity',
                                      'uom_id', vendors=False, ing_type='base'),
                get_ingredients_table(self.active_ingredient_ids, 'product_id', 'readonly_quantity',
                                      'uom_id', vendors=False, ing_type='active'),
            ]
            for table in range(len(tables)):
                if tables[table]:
                    if not table:
                        tables[table] += generate_total_table(
                            ['Total Base in a batch (lb)', 'Total Base in a batch (%)', 'Base Ingredients Total Cost'],
                            ["{:.4f}".format(self.base_ingredients_total_quantity),
                             f'{round(self.base_ingredients_total_quantity_percent * 100, 2)}%',
                             round(self.base_ingredients_total_cost, 2)])
                    else:
                        tables[table] += generate_total_table(
                            ['Total Formula (mg)', 'Total Active in a batch (lb)', 'Total Active in a batch (%)',
                             'Total Active Cost'],
                            ["{:.4f}".format(self.active_ingredients_total_quantity),
                             "{:.4f}".format(self.readonly_active_ingredients_total_quantity),
                             f'{round(self.readonly_active_ingredients_total_quantity_percent * 100, 2)}%',
                             round(self.readonly_active_ingredients_total_cost, 2)])

            body = body.replace('%ingredients%', Markup(''.join(filter(None, tables))))
        return get_mail_action(self.active_calculator_id, self.display_name, body, self.manufacturing_partner_id, False)


class ProductCalculator(models.Model):
    _name = 'product.calculator'
    _description = 'Product Calculator'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.constrains('active_ingredient_ids', 'base_ingredient_ids')
    def _check_ingredients_is_unique(self):
        for rec in self:
            msg = check_ingredients_is_unique({'Active': 'active_ingredient_ids', 'Base': 'base_ingredient_ids'}, rec)
            if msg:
                raise ValidationError('\n'.join(msg))

    portion_grams = fields.Float(
        string="Serving Size (Total gr.)",
        digits=(16, 1),
        default=1,
    )
    result_product_tmpl_id = fields.Many2one(
        'product.template',
        string='Result Product',
        copy=False,
    )
    one_batch_lb = fields.Float(
        string='One Batch Lb',
        default=lambda rec: get_default(rec, 'aznut_calculator.product_calculator_settings_main', 'one_batch_lb'),
        digits=(16, 3),
    )
    jar_weight = fields.Float(
        string='Jar size',
        digits=(16, 1),
    )
    ready_jar_cost = fields.Float(
        string='Price per jar',
        compute='_compute_ready_jar_cost_discount_amount',
        digits=(16, 2),
    )
    active_cost = fields.Float(
        string='Active',
        compute='_compute_readonly_fields',
        digits=(16, 3),
    )
    base_cost = fields.Float(
        string='Base',
        compute='_compute_readonly_fields',
        digits=(16, 3),
    )
    total_cost = fields.Float(
        string='Total ingredients',
        readonly=True,
        digits=(16, 3),
        compute='_compute_readonly_fields',
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
    )
    label_price = fields.Float(
        string='Label',
        digits=(16, 3),
    )
    shrink_price = fields.Float(
        string='Shrink',
        digits=(16, 3),
    )
    operating_expenses = fields.Float(
        string='Operating Expenses',
        compute='_compute_readonly_fields',
        digits=(16, 3),
    )
    monthly_exp = fields.Integer(
        string='Monthly Expenses',
        default=lambda rec: get_default(rec, 'aznut_calculator.product_calculator_settings_main',
                                        'monthly_expenses_preset'),
    )
    jars_per_month = fields.Integer(
        string='Jars Per Month',
        default=lambda rec: get_default(rec, 'aznut_calculator.product_calculator_settings_main',
                                        'jar_per_months_preset'),
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
    probiotic_portion = fields.Float(
        string='Probiotic per portion',
        compute='_compute_readonly_fields',
        digits=(16, 2),
    )
    active_ingredient_ids = fields.Many2many(
        'active.ingredient',
        'calculator_id',
        string='Active Ingredients',
        copy=False,
    )
    readonly_active_ingredient_ids = fields.Many2many(
        'active.ingredient',
        string='Active Ingredients',
        related='active_ingredient_ids',
    )
    base_ingredient_ids = fields.Many2many(
        'base.ingredient',
        string='Base Ingredients',
        default=lambda rec: [i.copy().id for i in
                             (get_default(rec, 'aznut_calculator.product_calculator_settings_main',
                                          'base_ingredient_ids') or rec.env['base.ingredient']).sorted(
                                 'sequence')],
        copy=False,
    )
    base_ingredients_total_cost = fields.Float(
        string='Base Ingredients Total Cost',
        compute='_compute_base_ingredients_totals',
    )
    base_ingredients_total_quantity = fields.Float(
        string='Base Ingredients Total Quantity',
        compute='_compute_base_ingredients_totals',
        digits=(16, 4),
    )
    base_ingredients_total_quantity_percent = fields.Float(
        string='Base Ingredients Total Quantity Percent',
        compute='_compute_base_ingredients_totals',
    )
    base_ingredients_total_quantity_diff = fields.Float(
        string='Base Ingredients Total Quantity',
        compute='_compute_base_ingredients_totals',
        digits=(16, 4),
    )

    readonly_active_ingredients_total_cost = fields.Float(
        string='Readonly Active Ingredients Total Cost',
        compute='_compute_readonly_active_ingredients_totals',
    )
    readonly_active_ingredients_total_quantity = fields.Float(
        string='Readonly Active Ingredients Total Quantity',
        compute='_compute_readonly_active_ingredients_totals',
        digits=(16, 4),
    )

    readonly_active_ingredients_total_quantity_diff = fields.Float(
        string='Readonly Active Ingredients Total Quantity',
        compute='_compute_readonly_active_ingredients_totals',
        digits=(16, 4),
    )
    cfu_portion_uom = fields.Selection(
        selection=[('bn', 'BN'), ('m', 'M')],
        default='bn',
    )
    bacteria_gram_base = fields.Integer(
        string='Bacteria grams base',
        default=lambda rec: get_default(rec, 'aznut_calculator.product_calculator_settings_main',
                                        'bacteria_gram_base'),
    )
    bacteria_gram_exponent = fields.Integer(
        string='Bacteria grams exponent',
        default=lambda rec: get_default(rec, 'aznut_calculator.product_calculator_settings_main',
                                        'bacteria_gram_exponent'),
    )
    product_name = fields.Char(
        string='Product Name',
        compute='_compute_product_name',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
    )
    calculator_type = fields.Selection(
        [('product', 'Product'), ('custom', 'Custom')],
        required=True,
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
    chews_per_jar = fields.Integer(
        string='Chews per jar',
    )
    chew_size = fields.Float(
        string='Each Chew Size',
        digits=(16, 1),
    )
    moq = fields.Float(
        string='MOQ, units',
        compute='_compute_moq',
        digits=(16, 0),
    )
    count_of_jars = fields.Integer(
        string='Count of Jars',
    )
    flavour_ids = fields.Many2many(
        'product.product',
        string='Flavour',
        domain=lambda rec: [
            ('categ_id', '=', rec.env.ref('aznut_calculator.product_calculator_settings_main').flavour_category_id.id)],
    )
    total_price = fields.Float(
        'Total Order',
        compute='_compute_total_price',
        digits=(16, 2),
    )
    lead_time = fields.Text(
        string='Lead Time',
        default=lambda rec: get_default(rec, 'aznut_calculator.product_calculator_settings_main', 'lead_time'),
    )
    discount_amount = fields.Float(
        string='Discount',
        digits=(16, 2),
        store=True,
    )
    profit = fields.Float(
        string='Profit',
        digits=(16, 2),
        default=lambda rec: get_default(rec, 'aznut_calculator.product_calculator_settings_main', 'profit'),
    )
    shipping = fields.Float(
        string='Shipping',
        digits=(16, 2),
        compute='_compute_shipping'
    )
    note = fields.Html(
        string='Note',
    )
    report_base_ingredients = fields.Char(
        string='Base Ingredients List:',
        compute='_compute_report_base_ingredients',
        store=True,
    )
    active_ingredients_total_quantity = fields.Float(
        string='Total Qty',
        compute='_compute_active_ingredients_total_qty',
        digits=(16, 4)
    )
    shape_ids = fields.Many2many(
        'product.calculator.settings.shape',
        string='Shape',
    )
    net_cost = fields.Float(
        string='Net Cost',
        compute='_compute_readonly_fields'
    )

    use_active_multiply = fields.Boolean(
        string="Add 15% to active quantity output",
        default=False,
    )
    readonly_active_ingredients_total_quantity_percent = fields.Float(
        string='Readonly Active Ingredients Total Quantity Percent',
        compute='_compute_readonly_active_ingredients_totals',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.user.company_id.currency_id,
    )
    taxes = fields.Float(
        string='Taxes',
        digits=(16, 2),
        default=lambda rec: get_default(rec, 'aznut_calculator.product_calculator_settings_main', 'taxes'),
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
                'aznut_calculator.product_calculator_settings_main').dog_treats_packaging_materials_category_id.id)],
    )
    shrink_product_id = fields.Many2one(
        'product.product',
        string='Shrink Product',
        domain=lambda rec: [
            ('categ_id', '=', rec.env.ref(
                'aznut_calculator.product_calculator_settings_main').dog_treats_packaging_materials_category_id.id)],
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
    is_user_calculator_procurement = fields.Boolean(
        string='Is User Calculator Procurement',
        compute="_compute_is_user_calculator_procurement",
    )
    is_calculator_administrator = fields.Boolean(
        string='Is Calculator Administrator',
        compute='_compute_is_calculator_administrator_manager',
    )
    is_calculator_manager = fields.Boolean(
        string='Is Calculator Manager',
        compute='_compute_is_calculator_administrator_manager',

    )
    is_calculator_salesperson = fields.Boolean(
        string='Is Calculator Salesperson',
        compute='_compute_is_calculator_salesperson',
    )

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, rec.product_name))
        return res

    @api.depends('product_id')
    def _compute_product_name(self):
        for calculator in self:
            calculator.product_name = calculator.product_id.name or 'No Product'

    def _compute_is_calculator_administrator_manager(self):
        is_admin = self.env.user.has_group('aznut_calculator.group_calculator_administrator')
        is_manager = self.env.user.has_group('aznut_calculator.group_calculator_manager')
        self.is_calculator_administrator = True if is_admin else False
        self.is_calculator_manager = True if is_manager else False

    def _compute_is_user_calculator_procurement(self):
        calculator_procurement = self.env.user.has_group('aznut_calculator.group_calculator_procurement')
        self.is_user_calculator_procurement = calculator_procurement

    def _compute_is_calculator_salesperson(self):
        calculator_salesperson = self.env.user.has_group('aznut_calculator.group_calculator_salesperson')
        self.is_calculator_salesperson = calculator_salesperson

    @api.depends('manufacturing_partner_id')
    def _compute_manufacturing_reply(self):
        self.manufacturing_reply = CHAT_TEMPLATE % ''
        for product_calculator in self:
            messages = self.env['mail.message'].sudo().search([
                ('res_id', '=', product_calculator.id),
                ('model', '=', product_calculator._name),
                ('author_id', '=', product_calculator.manufacturing_partner_id.id),
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
                product_calculator.manufacturing_reply = Markup(CHAT_TEMPLATE % html)

    @api.depends('procurement_partner_id')
    def _compute_procurement_reply(self):
        self.procurement_reply = CHAT_TEMPLATE % ''
        for product_calculator in self:
            messages = self.env['mail.message'].sudo().search([
                ('res_id', '=', product_calculator.id),
                ('model', '=', product_calculator._name),
                ('author_id', '=', product_calculator.procurement_partner_id.id),
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
                product_calculator.procurement_reply = Markup(CHAT_TEMPLATE % html)

    def _compute_ask_gpt_session_id(self):
        self.ask_gpt_session_id = False
        for product_calculator in self:
            product_calculator.ask_gpt_session_id = self.env['ask.gpt.session'].search([
                ('product_calculator_id', '=', product_calculator.id),
            ], limit=1)

    def _compute_jar_products_ids(self):
        settings = self.env.ref('aznut_calculator.product_calculator_settings_main')
        for calculator in self:
            calculator.jar_products_ids = settings.jar_products_ids

    def _compute_shipping(self):
        shipping_preset = self.env.ref('aznut_calculator.product_calculator_settings_main').shipping_cost
        self.shipping = 0
        for rec in self:
            if rec.jar_weight:
                shipping = (rec.one_batch_lb * shipping_preset) / (8320 / rec.jar_weight)
                rec.shipping = round(shipping * 20) / 20.0

    def _compute_total_price(self):
        self.total_price = 0
        for rec in self:
            if rec.ready_jar_cost and rec.count_of_jars:
                rec.total_price = rec.ready_jar_cost * rec.count_of_jars

    def _compute_moq(self):
        for rec in self:
            rec.moq = rec._calculate_moq()

    def _compute_readonly_active_ingredient_ids(self):
        for rec in self:
            rec.readonly_active_ingredient_ids = rec.active_ingredient_ids

    def _compute_readonly_fields(self):
        self.probiotic_portion = 0
        self.active_cost, self.base_cost, self.total_cost = 0, 0, 0
        self.operating_expenses = 0
        for rec in self:
            if rec.bacteria_gram and rec.cfu_portion and rec.bacteria_gram_base and rec.bacteria_gram_exponent:
                if rec.cfu_portion_uom == 'bn':
                    cfu_portion_calculated = rec.cfu_portion * 1000000000
                if rec.cfu_portion_uom == 'm':
                    cfu_portion_calculated = rec.cfu_portion * 1000000
                bacteria_gram_calculated = rec.bacteria_gram_base ** rec.bacteria_gram_exponent * rec.bacteria_gram
                rec.probiotic_portion = 1000 / (bacteria_gram_calculated / cfu_portion_calculated)
            if rec.jars_per_month:
                ratio = rec.monthly_exp / rec.jars_per_month
                rec.operating_expenses = ratio
            if rec.jar_weight:
                one_batch_lb = rec.one_batch_lb
                jar_weight_formula = one_batch_lb * 16 / rec.jar_weight
                active_ingredients_cost = rec.readonly_active_ingredients_total_cost
                base_ingredients_cost = rec.base_ingredients_total_cost
                rec.base_cost = base_ingredients_cost / jar_weight_formula
                rec.active_cost = active_ingredients_cost / jar_weight_formula
                rec.total_cost = rec.base_cost + rec.active_cost
            rec.net_cost = rec.total_cost + rec.label_price + rec.lid_price + rec.jar_price + rec.shrink_price + rec.box_price + rec.shipping + rec.taxes

    def _compute_ready_jar_cost_discount_amount(self):
        self.ready_jar_cost = False
        for rec in self:
            shape_cost = sum(rec.shape_ids.mapped('cost'))
            ready_jar_cost = sum([rec.total_cost, rec.jar_price, rec.lid_price, rec.box_price, rec.profit,
                                  rec.shipping, rec.label_price, rec.shrink_price, rec.operating_expenses,
                                  shape_cost, rec.taxes]) - rec.discount_amount
            rec.ready_jar_cost = ready_jar_cost

    def _compute_base_ingredients_totals(self):
        settings = self.env.ref('aznut_calculator.product_calculator_settings_main')
        settings_quantity = settings.base_ingredients_quantity
        for rec in self:
            if rec.readonly_active_ingredients_total_quantity:
                auto_adjusted_ingredient = rec.base_ingredient_ids.filtered(
                    lambda ing: ing.product_id.id in settings.auto_adjusted_base_ingredients_ids.ids).sorted('sequence')[:1]
                total_quantity_diff = rec.one_batch_lb - rec.readonly_active_ingredients_total_quantity - sum(
                    rec.base_ingredient_ids.mapped('quantity'))
                auto_adjusted_ingredient.quantity += total_quantity_diff
            base_ingredients_total_cost = sum(rec.base_ingredient_ids.mapped('total_cost'))
            base_ingredients_total_quantity = sum(rec.base_ingredient_ids.mapped('quantity'))
            rec.base_ingredients_total_cost = base_ingredients_total_cost
            rec.base_ingredients_total_quantity = base_ingredients_total_quantity
            rec.base_ingredients_total_quantity_percent = base_ingredients_total_quantity / 520
            rec.base_ingredients_total_quantity_diff = round(settings_quantity - base_ingredients_total_quantity, 2)

    def _compute_readonly_active_ingredients_totals(self):
        settings = self.env.ref('aznut_calculator.product_calculator_settings_main')
        settings_quantity = settings.readonly_active_ingredients_quantity
        one_batch_lb = settings.one_batch_lb

        for rec in self:
            readonly_active_ingredients_total_cost = rec.readonly_active_ingredient_ids.mapped('total_cost')
            readonly_active_ingredients_total_quantity = rec.readonly_active_ingredient_ids.mapped('readonly_quantity')
            rec.readonly_active_ingredients_total_cost = sum(readonly_active_ingredients_total_cost)
            rec.readonly_active_ingredients_total_quantity = sum(readonly_active_ingredients_total_quantity)
            rec.readonly_active_ingredients_total_quantity_percent = rec.readonly_active_ingredients_total_quantity / one_batch_lb
            rec.readonly_active_ingredients_total_quantity_diff = round(
                settings_quantity - rec.readonly_active_ingredients_total_quantity, 2)

    @api.depends('base_ingredient_ids.name', 'base_ingredient_ids.sequence')
    def _compute_report_base_ingredients(self):
        for child_calculator in self:
            base_ingredients = child_calculator.base_ingredient_ids.sorted('sequence')
            child_calculator.report_base_ingredients = ', '.join(
                base_ingredients.filtered(lambda ing: ing.name).mapped('name'))

    def unlink(self):
        self.base_ingredient_ids.unlink()
        self.active_ingredient_ids.unlink()
        return super(ProductCalculator, self).unlink()

    def _get_order_details(self):
        order_details = self.read(order_details_fields)[0]
        names = self.fields_get(order_details_fields)
        prepared_details = []
        for val in names:
            if order_details[val] or val in ['jar_exist', 'lid_exist', 'label_exist']:
                if val == 'flavour_ids':
                    flavour_names = self.env['product.product'].search(
                        [('id', 'in', order_details[val])])
                    prepared_details.append({'val': flavour_names.mapped('name'), 'name': names[val]['string']})
                elif val == 'shape_ids':
                    shape_names = self.env['product.calculator.settings.shape'].search(
                        [('id', 'in', order_details[val])])
                    prepared_details.append({'val': ', '.join(shape_names.mapped('name')), 'name': names[val]['string']})
                elif val == 'chews_per_jar':
                    value = '{:,} / Jar'.format(order_details[val])
                    prepared_details.append({'val': value, 'name': 'Approximate Chews'})
                elif val in ['portion_grams', 'chew_size']:
                    value = '{:,.1f} g'.format(order_details[val])
                    prepared_details.append({'val': value, 'name': names[val]['string']})
                elif val == 'jar_weight':
                    oz_value = order_details[val]
                    uom_from = self.env.ref('uom.product_uom_oz')
                    uom_to = self.env.ref('uom.product_uom_gram')
                    gram_value = uom_from._compute_quantity(oz_value, uom_to, False, 'HALF-UP', False)
                    value = '{:,.1f} oz / {:,.1f} g'.format(oz_value, gram_value)
                    prepared_details.append({'val': value, 'name': names[val]['string']})
                elif val == 'jar_product_id':
                    prepared_details.append({'val': order_details[val][1], 'name': 'Jar Finish'})
                elif val == 'lid_product_id':
                    prepared_details.append({'val': order_details[val][1], 'name': 'Lid Finish'})
                else:
                    value = order_details[val]
                    if isinstance(value, int):
                        value = '{:,}'.format(value)
                    elif isinstance(value, float):
                        value = '{:,.1f}'.format(order_details[val])
                    prepared_details.append({'val': value, 'name': names[val]['string']})
        return sorted(prepared_details, key=lambda x: order_details_names.index(x['name']))

    def _get_row_quantity(self):
        order_details = self._get_order_details()
        active_ingredients = self.readonly_active_ingredient_ids.mapped('name')
        return max(len(order_details), len(active_ingredients))

    def _get_cleaned_note(self):
        self.ensure_one()
        if not self.note:
            return self.note
        try:
            root = lxml_html.fragment_fromstring(self.note, create_parent='div')
        except Exception:
            return self.note

        return get_cleaned_note(root)

    def write(self, vals):
        vals_flavour = vals.get('flavour_ids')
        if vals_flavour:
            for old_flavour_id in self.flavour_ids.ids:
                if old_flavour_id not in vals_flavour[0][2]:
                    self.remove_product_from_flavour(old_flavour_id)
            for new_flavour_id in vals_flavour[0][2]:
                if new_flavour_id not in self.flavour_ids.ids:
                    self.add_product_from_flavour(new_flavour_id)
        rec = super(ProductCalculator, self).write(vals)
        if vals_flavour:
            self._compute_ready_jar_cost_discount_amount()
        return rec

    def remove_product_from_flavour(self, flavour_id):
        flavour = self.flavour_ids.filtered(lambda rec: rec.id == flavour_id)
        base_ingredient = self.base_ingredient_ids.filtered(lambda rec: rec.product_id.id == flavour.id)
        if base_ingredient.quantity > flavour.flavour_quantity:
            base_ingredient.quantity -= flavour.flavour_quantity
        else:
            self.write({
                'base_ingredient_ids': [Command.unlink(base_ingredient.id)]
            })

    def add_product_from_flavour(self, flavour_id):
        base_ingredient_product_ids = self.base_ingredient_ids.mapped('product_id.id')
        flavour = self.env['product.product'].browse(flavour_id)
        if flavour.id not in base_ingredient_product_ids:
            new_base_ingredient = self.env['base.ingredient'].create({
                'product_id': flavour.id,
                'quantity': flavour.flavour_quantity
            })
            self.write({'base_ingredient_ids': [(4, new_base_ingredient.id)]})
        else:
            base_ingredient = self.base_ingredient_ids.filtered(lambda rec: rec.product_id.id == flavour.id)
            base_ingredient.quantity += flavour.flavour_quantity

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        rec = super(ProductCalculator, self).copy(default)
        active_ingredients_ids = [i.copy().id for i in self.active_ingredient_ids.sorted('sequence')]
        active_ingredients = self.env['active.ingredient'].browse(active_ingredients_ids)
        active_ingredients.write({'calculator_id': rec.id})
        vals = {
            'base_ingredient_ids': [i.copy().id for i in self.base_ingredient_ids.sorted('sequence')],
            'active_ingredient_ids': active_ingredients.ids,
        }
        rec.write(vals)
        return rec

    def _compute_active_ingredients_total_qty(self):
        for rec in self:
            active_ingredients = self.active_ingredient_ids.mapped('quantity')
            rec.active_ingredients_total_quantity = sum(active_ingredients)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        return res

    def _calculate_moq(self):
        self.ensure_one()
        if self.jar_weight:
            moq = round(self.one_batch_lb * 16 / self.jar_weight, -2)
            return moq * 2 if moq <= 1000 else moq
        return 0


class IngredientMixin(models.AbstractModel):
    _name = 'ingredient.mixin'
    _description = 'Ingredient Mixin'

    name = fields.Char(
        string='Name',
        related='product_id.name',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        # required=True,
        domain=lambda rec: [('uom_id', '=', rec.env.ref('uom.product_uom_lb').id)],
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
    quantity = fields.Float(
        string='Quantity',
        digits=(16, 4),
        default=1,
    )
    total_cost = fields.Float(
        string='Total Cost',
        compute='_compute_total_cost',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.user.company_id.currency_id)

    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        compute='_compute_cost_per_lb_uom_id',
        store=True,
    )
    cost_per_lb = fields.Float(
        string='Cost Per LB',
        compute='_compute_cost_per_lb_uom_id',
        store=True,
    )
    seq_number = fields.Integer(
        string='No.',
        compute='_compute_seq_number',
    )

    def _compute_seq_number(self):
        calculate_seq_number(self)

    @api.depends('product_id')
    def _compute_cost_per_lb_uom_id(self):
        for rec in self:
            rec.cost_per_lb = rec.product_id.standard_price
            rec.uom_id = rec.product_id.uom_id

    @api.depends('product_id', 'quantity', 'cost_per_lb')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.quantity * rec.cost_per_lb


class ActiveIngredient(models.Model):
    _name = 'active.ingredient'
    _description = 'Active Ingredient'
    _inherit = ['ingredient.mixin']

    color = fields.Selection(
        [('blue', 'Blue'), ('red', 'Red'), ('yellow', 'Yellow'), ('green', 'Green')],
    )
    comments = fields.Char(
        string='Comments',
    )
    active_ingredient_uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        compute='_compute_active_ingredient_uom_id',
        store=True,
    )
    product_id = fields.Many2one(
        'product.product',
        domain=lambda rec: ['&', ('uom_id', '=', rec.env.ref('uom.product_uom_lb').id), '|',
                            ('calculator_uom_id', '=', rec.env.ref('aznut_calculator.product_uom_mg').id),
                            ('calculator_uom_id', '=', rec.env.ref('uom.product_uom_gram').id)],
    )
    readonly_quantity = fields.Float(
        string='Quantity',
        compute='_compute_readonly_quantity',
        digits=(16, 4),
    )
    calculator_id = fields.Many2one(
        'product.calculator',
        string='Calculator',
    )
    ingredient_cost_per_jar = fields.Float(
        string='Cost Ingredient Per Jar',
        compute='_compute_ingredient_cost_per_jar'
    )
    forecast_availability = fields.Float(
        string='Forecast Availability',
        compute='_compute_forecast_information',
        digits=(16, 16),
        compute_sudo=True,
    )

    @api.depends('quantity')
    def _compute_forecast_information(self):
        for ingredient in self:
            uom_from = ingredient.product_id.uom_id
            uom_to = ingredient.active_ingredient_uom_id
            quantity = uom_to._compute_quantity(ingredient.quantity, uom_from, False, 'HALF-UP', False)
            ingredient.forecast_availability = ingredient.product_id.qty_available - quantity

    def _compute_ingredient_cost_per_jar(self):
        lb_uom = self.env.ref('uom.product_uom_lb')
        oz_uom = self.env.ref('uom.product_uom_oz')
        for rec in self:
            if rec.calculator_id.jar_weight:
                one_batch_lb = rec.calculator_id.one_batch_lb / rec.calculator_id.jar_weight
                batch_size = lb_uom._compute_quantity(one_batch_lb, oz_uom, False, 'HALF-UP', False)
                rec.ingredient_cost_per_jar = rec.total_cost / batch_size if batch_size else 0
            else:
                rec.ingredient_cost_per_jar = 0

    @api.depends('product_id')
    def _compute_active_ingredient_uom_id(self):
        for rec in self:
            rec.active_ingredient_uom_id = rec.product_id.calculator_uom_id

    @api.depends('quantity', 'product_id')
    def _compute_readonly_quantity(self):
        self.readonly_quantity = 0
        for rec in self.filtered(lambda ingredient: ingredient.calculator_id):
            one_batch_g = rec.calculator_id.one_batch_lb * 453.592
            if rec.calculator_id.portion_grams and rec.active_ingredient_uom_id.factor:
                quantity_kg = rec.quantity / rec.active_ingredient_uom_id.factor
                quantity_lb = quantity_kg * rec.uom_id.factor
                rec.readonly_quantity = quantity_lb * (one_batch_g / rec.calculator_id.portion_grams)
                if rec.calculator_id.use_active_multiply:
                    rec.readonly_quantity = rec.readonly_quantity * 1.15

    @api.depends('product_id', 'quantity')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.readonly_quantity * rec.cost_per_lb


class BaseIngredient(models.Model):
    _name = 'base.ingredient'
    _description = 'Base Ingredient'
    _inherit = ['ingredient.mixin']

    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        compute='_compute_cost_per_lb_uom_id',
        store=True,
    )
    forecast_availability = fields.Float(
        string='Forecast Availability',
        compute='_compute_forecast_information',
        digits=(16, 16),
        compute_sudo=True,
    )

    @api.depends('quantity')
    def _compute_forecast_information(self):
        for ingredient in self:
            uom_from = ingredient.product_id.uom_id
            uom_to = ingredient.uom_id
            quantity = uom_to._compute_quantity(ingredient.quantity, uom_from, False, 'HALF-UP', False)
            ingredient.forecast_availability = ingredient.product_id.qty_available - quantity

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        rec = super(BaseIngredient, self).copy(default)
        rec.write({'cost_per_lb': self.cost_per_lb, 'uom_id': self.uom_id.id, 'sequence': self.sequence})
        return rec
