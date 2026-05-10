from odoo import models, fields, api


class WorkorderScrapLine(models.Model):
    _name = 'workorder.scrap.line'
    _description = 'Workorder Scrap Line'

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        readonly=True,
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        required=True,
        domain="[('category_id', '=', product_uom_category_id)]",
    )
    quantity = fields.Float(
        string='Quantity',
    )
    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id',
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        default=lambda self: self.env['stock.scrap']._get_default_location_id(),
        domain="[('usage', '=', 'internal'), ('company_id', 'in', [company_id, False])]",
    )
    workorder_id = fields.Many2one(
        'mrp.workorder',
        string='Workorder',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    lot_id = fields.Many2one(
        'stock.production.lot',
        string='Lot/Serial',
    )
    allowed_lot_ids = fields.Many2many(
        'stock.production.lot',
        string='Lots',
        compute="_compute_allowed_lot_ids",
    )
    done_quantity = fields.Float(
        string='Done Quantity',
        readonly=True,
    )

    @api.onchange('location_id', 'product_id', 'quantity')
    def _onchange_parameters(self):
        self.lot_id = False

    @api.depends('product_id', 'location_id', 'quantity')
    def _compute_allowed_lot_ids(self):
        for line in self:
            suitable_quants = self.env['stock.quant'].search([
                ('location_id', 'child_of', line.location_id.id),
                ('product_id', '=', line.product_id.id),
            ]).filtered(lambda quant: quant.available_quantity >= line.quantity)
            line.allowed_lot_ids = suitable_quants.mapped('lot_id')

    def action_add(self):
        self.ensure_one()
        scrap = self.env['stock.scrap'].create({
            'product_id': self.product_id.id,
            'scrap_qty': self.quantity,
            'location_id': self.location_id.id,
            'product_uom_id': self.uom_id.id,
            'lot_id': self.lot_id.id,
            'company_id': self.workorder_id.company_id.id,
            'workorder_id': self.workorder_id.id,
        })
        result = scrap.with_context(default_production_id=self.workorder_id.production_id.id).action_validate()
        if isinstance(result, bool):
            self.done_quantity += self.quantity
            scrap.write({
                'production_id': self.workorder_id.production_id.id,
            })
        return result
