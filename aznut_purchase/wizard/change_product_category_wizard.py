from odoo import fields, models


class ChangeProductCategoryWizard(models.TransientModel):
    _name = 'change.product.category.wizard'
    _description = 'Change Product Category Wizard'

    categ_id = fields.Many2one(
        'product.category',
        string='Category',
    )
    wizard_line_ids = fields.One2many(
        'change.product.category.wizard.line',
        'wizard_id',
        string='Lines',
    )

    def action_confirm(self):
        self.ensure_one()
        self.wizard_line_ids.mapped('product_template_id').write({
            'categ_id': self.categ_id.id,
        })


class ChangeProductCategoryWizardLine(models.TransientModel):
    _name = 'change.product.category.wizard.line'
    _description = 'Change Product Category Wizard Line'

    product_template_id = fields.Many2one(
        'product.template',
        string='Product Template',
    )
    categ_id = fields.Many2one(
        'product.category',
        related='product_template_id.categ_id',
    )
    wizard_id = fields.Many2one(
        'change.product.category.wizard',
        string='Wizard',
    )
