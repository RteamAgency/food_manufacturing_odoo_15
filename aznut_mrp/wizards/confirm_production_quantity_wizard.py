from odoo import fields, models, api
from odoo.exceptions import ValidationError


def update_move_done_quantity(move, qty_to_confirm):
    move.write({'product_uom_qty': qty_to_confirm})
    move._action_assign()
    move_lines = move.move_line_ids
    for line in move_lines:
        line.write({'qty_done': line.product_uom_qty})
    move._action_done()


class ConfirmProductionQuantityWizard(models.TransientModel):
    _name = 'confirm.production.quantity.wizard'
    _description = 'Confirm Production Quantity Wizard'

    @api.constrains('actual_quantity')
    def _check_actual_quantity(self):
        for wizard in self:
            if wizard.actual_quantity <= 0:
                raise ValidationError('Need To Provide Correct Actual Quantity!')

    wizard_production_id = fields.Many2one(
        'mrp.production',
        string='Production',
        required=True,
        readonly=True,
    )
    wizard_workorder_id = fields.Many2one(
        'mrp.workorder',
        string='Workorder',
    )
    quantity = fields.Float(
        string='Quantity',
        related='wizard_production_id.qty_producing'
    )
    actual_quantity = fields.Float(
        string='New Quantity',
    )

    def action_confirm(self):
        self.ensure_one()
        self = self.sudo()
        diff = self.actual_quantity - self.quantity
        production_vals = {
            'is_quantity_confirmed': True,
        }
        if diff and self.wizard_production_id.state != 'cancel' and not (
                self.wizard_production_id.state != 'done' and self.wizard_production_id.is_locked):
            production = self.wizard_production_id
            sale = self.wizard_production_id.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id
            production_vals.update({
                'qty_producing': production.qty_producing + diff,
            })
            product = self.wizard_production_id.product_id

            sale_line = sale.order_line.filtered(lambda line: line.product_id.id == product.id)
            if sale_line:
                sale_line.with_context(not_create_mo=True).write({
                    'product_uom_qty': sale_line.product_uom_qty + diff,
                })
            self.wizard_production_id.write(production_vals)
            for move in self.wizard_workorder_id.mapped('move_raw_ids'):
                update_move_done_quantity(move, move.should_consume_qty)
            self.wizard_production_id._confirm_quantity_moves()
        else:
            self.wizard_production_id.write(production_vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'views': [[self.env.ref('mrp_workorder.mrp_workorder_view_form_tablet').id, 'form']],
            'res_id': self.wizard_workorder_id.id,
            'target': 'fullscreen',
            'flags': {
                'withControlPanel': False,
                'form_view_initial_mode': 'edit',
            },
            'context': {
                'from_production_order': True,
                'active_id': self.wizard_workorder_id.id,
            },
        }
