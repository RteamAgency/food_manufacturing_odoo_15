from odoo import fields, models
from odoo.exceptions import ValidationError


class MoveReserveWizard(models.TransientModel):
    _name = 'move.reserve.wizard'
    _description = 'Move Reserve Wizard'

    move_id = fields.Many2one(
        'stock.move',
        string='Move',
    )
    move_reserve_wizard_line_ids = fields.One2many(
        'move.reserve.wizard.line',
        'reserve_wizard_id',
        string='Reserve Lines',
    )

    def action_confirm(self):
        self.ensure_one()
        self.move_id._do_unreserve()
        available_quantities = {line.id: self.move_id._get_available_quantity(
            line.location_id, lot_id=line.lot_id, package_id=line.package_id, owner_id=line.owner_id, strict=True
        ) for line in self.move_reserve_wizard_line_ids}
        invalid_lines = self.move_reserve_wizard_line_ids.filtered(
            lambda line: line.new_quantity > available_quantities.get(line.id)
        )
        lines_total = sum(self.move_reserve_wizard_line_ids.mapped('new_quantity'))
        if invalid_lines:
            raise ValidationError('Not enough quantity on stock:\n%s' % '\n'.join(['%s%s%s%s: %s - %s (Available)' % (
                line.location_id.display_name, ' & %s' % line.lot_id.display_name if line.lot_id else '',
                ' & %s' % line.owner_id.display_name if line.owner_id else '',
                ' & %s' % line.package_id.display_name if line.package_id else '', line.new_quantity,
                available_quantities.get(line.id)) for line in invalid_lines]))
        elif lines_total > self.move_id.product_uom_qty:
            raise ValidationError('Total sum of new quantities is greater consume quantity: %s > %s' % (
                lines_total, self.move_id.product_uom_qty))

        for line in self.move_reserve_wizard_line_ids:
            self.move_id.with_context(
                lot_id=line.lot_id, missing_quantity=line.new_quantity, location_id=line.location_id
            )._action_assign()
            self.move_id._recompute_state()


class MoveReserveWizardLine(models.TransientModel):
    _name = 'move.reserve.wizard.line'
    _description = 'Move Reserve Wizard Line'

    reserve_wizard_id = fields.Many2one(
        'move.reserve.wizard',
        string='Reserve Wizard',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        related='reserve_wizard_id.move_id.product_id'
    )
    lot_id = fields.Many2one(
        'stock.production.lot',
        string='Lot',
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        required=True,
    )
    owner_id = fields.Many2one(
        'res.partner',
        string='From Owner',
    )
    package_id = fields.Many2one(
        'stock.quant.package',
        string='Source Package',
    )
    new_quantity = fields.Float(
        string='Quantity',
        required=True,
    )
