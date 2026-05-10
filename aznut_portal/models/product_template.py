from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand = fields.Char(
        string='Brand',
        store=True,
        compute='_compute_brand',
    )
    brand_id = fields.Many2one(
        'product.attribute.value',
        string='Brand Record',
        store=True,
        compute='_compute_brand',
    )
    is_brand_empty = fields.Boolean(
        string='Is Brand Empty',
        store=True,
        compute='_compute_brand',
    )
    tags_history_lines_ids = fields.Many2many(
        'tag.history.line',
        string='Tags History Lines',
        compute='_compute_tags_history_lines_ids',
    )

    def _compute_tags_history_lines_ids(self):
        for prd_tmpl in self:
            prd_tmpl.tags_history_lines_ids = prd_tmpl.mapped('product_variant_ids.tags_history_lines_ids')

    @api.depends('attribute_line_ids')
    def _compute_brand(self):
        self.brand, self.is_brand_empty = False, True
        for prd_tmpl in self.filtered(lambda tmpl: tmpl.attribute_line_ids):
            brand_lines = prd_tmpl.attribute_line_ids.filtered(lambda line: line.attribute_id.name.lower() == 'brand')
            suitable_brand = brand_lines.sorted('create_date')[:1]
            brand = suitable_brand.value_ids.sorted('sequence')[:1]
            if brand:
                prd_tmpl.brand, prd_tmpl.is_brand_empty, prd_tmpl.brand_id = brand, False, brand.id

    def _get_batches_count(self, qty):
        if 1 <= self.batch and not qty % self.batch:
            batches_count = qty / self.batch
        else:
            batches_count = 0
        return batches_count


class ProductProduct(models.Model):
    _inherit = 'product.product'

    tags_history_lines_ids = fields.Many2many(
        'tag.history.line',
        string='Tags History Lines',
        compute='_compute_tags_history_lines_ids',
    )

    def _compute_tags_history_lines_ids(self):
        for product in self:
            so_lines = self.env['sale.order.line'].search([
                ('product_id', '=', product.id),
            ])
            so_orders = so_lines.mapped('order_id')
            product.tags_history_lines_ids = so_orders.mapped('tags_history_line_ids')
