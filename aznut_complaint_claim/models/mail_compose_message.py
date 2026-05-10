from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _action_send_mail(self, auto_commit=False):
        recall_id = self.env.context.get('recall_id')
        for wizard in self.filtered(lambda wzd: wzd.model == 'sale.order'):
            if recall_id:
                recall = self.env['recall.recall'].browse(recall_id)
                sale = self.env[wizard.model].browse(wizard.res_id)
                vals = {'recall_is_sent': True}
                if not sale.recall_id:
                    groups = self.env['procurement.group'].search([('sale_id', '=', sale.id)])
                    mos = groups.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids | groups.mrp_production_ids
                    if mos:
                        vals.update({'recall_id': recall.sudo().copy({'production_id': mos[:1].id,
                                                                      'name': self.env['ir.sequence'].next_by_code(
                                                                          'recall.recall') or 'New'}).id})
                sale.write(vals)
        return super(MailComposeMessage, self)._action_send_mail(auto_commit=auto_commit)
