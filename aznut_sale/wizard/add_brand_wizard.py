from odoo import api, fields, models


class AddBrandWizard(models.TransientModel):
    _name = 'add.brand.wizard'
    _description = 'Add Brand Wizard'

    products_ids = fields.Many2many(
        'product.template',
        string='Products',
        readonly=True,
        required=True,
    )
    brand_line_ids = fields.One2many(
        'add.brand.line',
        'wizard_id',
        string='Brand Lines',
        required=True,
    )
    allowed_attributes_ids = fields.Many2many(
        'product.attribute',
        readonly=True,
    )
    used_attributes_ids = fields.Many2many(
        'product.attribute',
        'user_attribute_rel',
        compute="_compute_used_attributes_ids",
    )

    @api.depends('brand_line_ids.attribute_id')
    def _compute_used_attributes_ids(self):
        for wizard in self:
            wizard.used_attributes_ids = wizard.brand_line_ids.mapped('attribute_id')

    def action_confirm(self):
        self.ensure_one()
        products = self.products_ids
        brand_lines = self.brand_line_ids

        attr_data = {
            brand_line.attribute_id.id: brand_line.value_ids.ids
            for brand_line in brand_lines
        }

        for prd_tmpl in products:
            existing_lines = {
                line.attribute_id.id: line
                for line in prd_tmpl.attribute_line_ids
                if line.attribute_id.id in attr_data
            }

            for attr_id, value_ids in attr_data.items():
                line = existing_lines.get(attr_id)
                if line:
                    line.write({'value_ids': value_ids})
                else:
                    line = self.env['product.template.attribute.line'].create({
                        'attribute_id': attr_id,
                        'product_tmpl_id': prd_tmpl.id,
                        'value_ids': value_ids
                    })
                    prd_tmpl.attribute_line_ids += line


class AddBrandLine(models.TransientModel):
    _name = 'add.brand.line'
    _description = 'Add Brand Line'

    attribute_id = fields.Many2one(
        'product.attribute',
        string='Attribute',
        required=True,
    )
    value_ids = fields.Many2many(
        'product.attribute.value',
        string='Values',
        required=True,
    )
    wizard_id = fields.Many2one(
        'add.brand.wizard',
        string='Wizard',
    )
