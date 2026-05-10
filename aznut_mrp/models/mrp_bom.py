from odoo import fields, models, api

from pytz import timezone, utc


def process_line(self, line=False, line_type='create', **kwargs):
    def msg_create(l, est_datetime):
        return f"<li>Line was created: quantity = {round(l.product_qty, 2)}, product = {l.product_id.name}. Date: {est_datetime.strftime('%Y-%m-%d %H:%M')}.</li>"

    def msg_unlink(p_name, p_qty, est_datetime):
        return f"<li>Line was deleted: quantity = {round(p_qty, 2)}, product = {p_name}. Date: {est_datetime.strftime('%Y-%m-%d %H:%M')}.</li>"

    description = None

    bom_id = line.bom_id.id if line else kwargs.get('bom_id')
    bom = self.env['mrp.bom'].browse(bom_id)

    est_dt = utc.localize(fields.Datetime.now()).astimezone(timezone('US/Eastern'))

    if line_type == 'create' and line:
        description = msg_create(line, est_dt)

    elif line_type == 'unlink':
        product = self.env['product.product'].browse(kwargs['old_product_id'])
        description = msg_unlink(product.name, kwargs['old_product_qty'], est_dt)

    elif line_type == 'write' and line:
        updates = []
        product = line.product_id
        if 'old_product_id' in kwargs:
            old_product = self.env['product.product'].browse(kwargs['old_product_id'])
            updates.append(f"product = {old_product.name} -> {line.product_id.name}")
            product = old_product
        if 'old_product_qty' in kwargs:
            updates.append(f"quantity = {round(kwargs['old_product_qty'], 2)} -> {round(line.product_qty, 2)}")
        if updates:
            description = f"<li>Line was updated ({product.name}): {', '.join(updates)}. Date: {est_dt.strftime('%Y-%m-%d %H:%M')}.</li>"
    if description:
        bom.message_post(body=description)


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    total_qty_lb = fields.Float(
        string="Total Quantity in lb",
        compute="_compute_total_qty",
    )
    total_qty_units = fields.Float(
        string="Total Quantity Units",
        compute="_compute_total_qty",
    )

    @api.depends('bom_line_ids')
    def _compute_total_qty(self):
        for rec in self:
            lb_products = rec.bom_line_ids.filtered(lambda line: line.product_uom_id.name == 'lb')
            unit_products = rec.bom_line_ids.filtered(lambda line: line.product_uom_id.name == 'Units')
            total_qty_lb = sum(lb_products.mapped('product_qty'))
            total_qty_units = sum(unit_products.mapped('product_qty'))
            rec.total_qty_lb = total_qty_lb
            rec.total_qty_units = total_qty_units


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    pump_uom = fields.Float(
        string="Pump qty",
        compute="_compute_pump_uom",
        digits=(4, 2),
    )

    @api.depends('product_uom_id', 'product_id.pump_ratio')
    def _compute_pump_uom(self):
        lb_uom = self.env.ref('uom.product_uom_lb')
        self.pump_uom = False
        for bom_line in self.filtered(lambda line: line.product_uom_id.id == lb_uom.id):
            bom_line.pump_uom = bom_line.product_id._get_pump_uom(bom_line.product_qty)

    def unlink(self):
        res = True
        for line in self:
            vals = {
                'old_product_id': line.product_id.id,
                'old_product_qty': line.product_qty,
                'bom_id': line.bom_id.id,
            }
            res &= super(MrpBomLine, line).unlink()
            process_line(self, False, 'unlink', **vals)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = self.env['mrp.bom.line']
        for vals in vals_list:
            line = super(MrpBomLine, self).create(vals)
            process_line(self, line, 'create', **{})
            lines |= line
        return lines

    def write(self, vals):
        res = True
        for line in self:
            changes = {}
            if 'product_id' in vals and vals['product_id'] != line.product_id.id:
                changes['old_product_id'] = line.product_id.id
            if 'product_qty' in vals and vals['product_qty'] != line.product_qty:
                changes['old_product_qty'] = line.product_qty
            res &= super(MrpBomLine, line).write(vals)
            if changes:
                process_line(self, line, 'write', **changes)
        return res
