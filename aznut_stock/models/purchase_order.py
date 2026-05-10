from odoo import fields, models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    receive_status = fields.Selection(
        selection=[('to_receive', 'To Receive'), ('received', 'Fully Received')],
        compute="_compute_purchase_receive_state",
        store="True",
        string="Receive Status"
    )
    
    @api.depends('picking_ids.state')
    def _compute_purchase_receive_state(self):
        for order in self:
            transfer_states = order.picking_ids.mapped('state')
            if all(state == 'cancel' for state in transfer_states):
                order.receive_status = "to_receive"
            elif all(state == 'done' for state in transfer_states) or all(state in ['done', 'cancel'] for state in transfer_states):
                order.receive_status = "received"
            else:
                order.receive_status = "to_receive"
