from odoo import fields, models


class CompareCalculatorMixin(models.AbstractModel):
    _name = 'compare.calculator.mixin'
    _description = 'Compare Calculator Mixin'

    main_calculator_id = fields.Many2one(
        'main.product.calculator',
        string='Main Chews Calculator',
        required=True,
    )
    calculators_ids = fields.Many2many(
        'product.calculator',
        related='main_calculator_id.calculator_ids',
    )
    calculator_first = fields.Many2one(
        'product.calculator',
        string='Product Calculator First',
    )
    calculator_second = fields.Many2one(
        'product.calculator',
        string='Product Calculator First',
    )
    count_of_jars_first = fields.Integer(
        related='calculator_first.count_of_jars',
    )
    count_of_jars_second = fields.Integer(
        related='calculator_second.count_of_jars',
    )
    currency_id = fields.Many2one(
        related='main_calculator_id.currency_id',
    )


class ProductCompareCalculatorWizard(models.TransientModel):
    _name = 'product.compare.calculator.wizard'
    _description = 'Product Compare Calculator Wizard'
    _inherit = 'compare.calculator.mixin'

    moq_first = fields.Float(
        related='calculator_first.moq',
    )
    moq_second = fields.Float(
        related='calculator_second.moq',
    )
    chews_per_jar_first = fields.Integer(
        related='calculator_first.chews_per_jar',
    )
    chews_per_jar_second = fields.Integer(
        related='calculator_second.chews_per_jar',
    )
    chew_size_first = fields.Float(
        related='calculator_first.chew_size',
    )
    chew_size_second = fields.Float(
        related='calculator_second.chew_size',
    )
    portion_grams_first = fields.Float(
        related='calculator_first.portion_grams',
    )
    portion_grams_second = fields.Float(
        related='calculator_second.portion_grams',
    )
    jar_weight_first = fields.Float(
        related='calculator_first.jar_weight',
    )
    jar_weight_second = fields.Float(
        related='calculator_second.jar_weight',
    )
    first_flavour_ids = fields.Many2many(
        related='calculator_first.flavour_ids',
        relation='first_calculator_flavour_rel'
    )
    second_flavour_ids = fields.Many2many(
        related='calculator_second.flavour_ids',
        relation='second_calculator_flavour_rel'
    )
    first_shape_ids = fields.Many2many(
        related='calculator_first.shape_ids',
        relation='first_calculator_shape_rel'
    )
    second_shape_ids = fields.Many2many(
        related='calculator_second.shape_ids',
        relation='second_calculator_shape_rel'
    )
    ready_jar_cost_first = fields.Float(
        related='calculator_first.ready_jar_cost',
    )
    ready_jar_cost_second = fields.Float(
        related='calculator_second.ready_jar_cost',
    )
    first_active_ingredient_ids = fields.Many2many(
        related='calculator_first.active_ingredient_ids',
        relation='first_calculator_active_ingredient_rel',
        inverse='_inverse_active_ingredient_ids',
        readonly=False,
    )
    second_active_ingredient_ids = fields.Many2many(
        related='calculator_second.active_ingredient_ids',
        relation='second_calculator_active_ingredient_rel',
        inverse='_inverse_active_ingredient_ids',
        readonly=False,
    )

    def _inverse_active_ingredient_ids(self):
        for rec in self:
            if rec.calculator_first:
                rec.calculator_first.active_ingredient_ids = rec.first_active_ingredient_ids
            if rec.calculator_second:
                rec.calculator_second.active_ingredient_ids = rec.second_active_ingredient_ids


class PowderCompareCalculatorWizard(models.TransientModel):
    _name = 'powder.compare.calculator.wizard'
    _description = 'Powder Compare Calculator Wizard'
    _inherit = 'compare.calculator.mixin'

    moq_first = fields.Integer(
        related='calculator_first.moq',
    )
    moq_second = fields.Integer(
        related='calculator_second.moq',
    )
    main_calculator_id = fields.Many2one(
        'main.powder.calculator',
        string='Main Powder Calculator',
        required=True,
    )
    calculators_ids = fields.One2many(
        'powder.calculator',
        related='main_calculator_id.powder_calculator_ids',
    )
    calculator_first = fields.Many2one(
        'powder.calculator',
        string='Powder Calculator First',
    )
    calculator_second = fields.Many2one(
        'powder.calculator',
        string='Powder Calculator First',
    )

    scoop_grams_jar_first = fields.Float(
        related='calculator_first.scoop_grams',
    )
    scoop_grams_jar_second = fields.Float(
        related='calculator_second.scoop_grams',
    )
    ordered_jars_number_first = fields.Integer(
        related='calculator_first.ordered_jars_number',
    )
    ordered_jars_number_second = fields.Integer(
        related='calculator_second.ordered_jars_number',
    )
    jar_size_gr_first = fields.Float(
        related='calculator_first.jar_size_gr',
    )
    jar_size_gr_second = fields.Float(
        related='calculator_second.jar_size_gr',
    )
    jar_size_oz_first = fields.Float(
        related='calculator_first.jar_size_oz',
    )
    jar_size_oz_second = fields.Float(
        related='calculator_second.jar_size_oz',
    )
    price_per_jar_first = fields.Float(
        related='calculator_first.price_per_jar',
    )
    price_per_jar_second = fields.Float(
        related='calculator_second.price_per_jar',
    )
    first_active_ingredient_ids = fields.One2many(
        related='calculator_first.active_ingredient_ids',
        inverse='_inverse_active_ingredient_ids',
        readonly=False,
    )
    second_active_ingredient_ids = fields.One2many(
        related='calculator_second.active_ingredient_ids',
        inverse='_inverse_active_ingredient_ids',
        readonly=False,
    )

    def _inverse_active_ingredient_ids(self):
        for rec in self:
            if rec.calculator_first:
                rec.calculator_first.active_ingredient_ids = rec.first_active_ingredient_ids
            if rec.calculator_second:
                rec.calculator_second.active_ingredient_ids = rec.second_active_ingredient_ids
