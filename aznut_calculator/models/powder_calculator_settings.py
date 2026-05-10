from odoo import fields, models


class MainPowderCalculatorSettings(models.Model):
    _name = 'powder.calculator.settings'
    _description = 'Main Powder Calculator Settings'

    scoop_grams = fields.Float(
        string='Each Scoop Size',
        digits=(16, 1),
    )
    ordered_jars_number = fields.Integer(
        string='Scoops per jar',
    )
    packaging_materials = fields.Float(
        string='Scoop Cost',
        digits=(16, 2),
    )
    name = fields.Char(
        required=True,
        readonly=True,
    )
    profit = fields.Float(
        string='Profit',
        digits=(16, 2),
    )
    taxes = fields.Float(
        string='Taxes',
        digits=(16, 2),
    )
    box_preset = fields.Float(
        string='Box'
    )
    label_preset = fields.Float(
        string='Label',
    )
    shrink_preset = fields.Float(
        string='Shrink'
    )
    count_of_jars = fields.Integer(
        string='Count of Jars',
    )
    monthly_expenses_preset = fields.Integer(
        string='Monthly Expenses'
    )
    jar_per_months_preset = fields.Integer(
        string='Jars Per Month'
    )
    bacteria_gram_base = fields.Integer(
        string='Bacteria grams base',
        default=10,
        required=True,
    )
    bacteria_gram_exponent = fields.Integer(
        string='Bacteria grams exponent',
        default=10,
        required=True,
    )
    shipping_cost = fields.Float(
        string='Shipping cost per lb',
    )
    taxes = fields.Float(
        string='Taxes',
        digits=(16, 2),
    )
    jar_labels_category_id = fields.Many2one(
        'product.category',
        string='Jar Labels Category',
    )
    dog_treats_packaging_materials_category_id = fields.Many2one(
        'product.category',
        string='Dog Treats Packaging Materials Category',
    )
    jar_products_ids = fields.Many2many(
        'product.product',
        string='Jar And Lid Products',
    )
    calculator_product_category_id = fields.Many2one(
        'product.category',
        string='Calculator Product Category',
    )


class PowderCalculatorMoqDiscount(models.Model):
    _name = 'powder.calculator.moq.discount'
    _description = 'Powder Calculator Moq Discount'

    divider = fields.Integer(
        string='Divider',
        required=True,
    )
    moq_discount = fields.Float(
        string='MOQ Discount',
        default=0
    )
