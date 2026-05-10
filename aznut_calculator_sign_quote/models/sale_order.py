from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    main_calculator_id = fields.Many2one(
        'main.product.calculator',
        string='Quote'
    )
    main_powder_calculator_id = fields.Many2one(
        'main.powder.calculator',
        string='Powder Quote'
    )
    total_sales_commission = fields.Float(
        string='Total Sales Commission',
        compute='_compute_total_sales_commission',
        store=True,
    )

    @api.depends('order_line.product_uom_qty', 'order_line.sales_commission')
    def _compute_total_sales_commission(self):
        for rec in self:
            rec.total_sales_commission = sum(
                map(lambda line: line.product_uom_qty * line.sales_commission, rec.order_line)
            )

    def show_product_quote(self):
        self.ensure_one()
        view_id = self.env.ref('aznut_calculator.main_product_calculator_form_view').id
        return {
            'name': 'Quote',
            'type': 'ir.actions.act_window',
            'res_model': 'main.product.calculator',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'create': 0},
            'res_id': self.main_calculator_id.id,
        }

    def show_powder_quote(self):
        self.ensure_one()
        view_id = self.env.ref('aznut_calculator.main_powder_calculator_form_view').id
        return {
            'name': 'Powder Quote',
            'type': 'ir.actions.act_window',
            'res_model': 'main.powder.calculator',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'create': 0},
            'res_id': self.main_powder_calculator_id.id,
        }


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    sales_commission = fields.Float(
        string='Sales Commission',
        digits=(16, 2),
        readonly=True,
    )

    @api.onchange('product_id')
    def product_id_change(self):
        self.sales_commission = self.product_id.sales_commission
        return super(SaleOrderLine, self).product_id_change()

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'sales_commission')
    def _compute_amount(self):
        super(SaleOrderLine, self)._compute_amount()
        for line in self:
            line.price_total += line.sales_commission * line.product_uom_qty
            line.price_subtotal += line.sales_commission * line.product_uom_qty
