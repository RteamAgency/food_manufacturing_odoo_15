from odoo import models, fields

from werkzeug.urls import url_join


class AccountMove(models.Model):
    _inherit = "account.move"

    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Opportunity',
        check_company=True,
        readonly=True,
        copy=False,
    )
    sale_order_from_invoice_id = fields.Many2one(
        'sale.order',
        string='Sale Order From Invoice',
        copy=False,
        readonly=True,
    )

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for move in self.filtered(
                lambda mv: mv.state == 'posted' and not mv.sale_order_from_invoice_id and mv.move_type == 'out_invoice'):
            created_orders = self.env['sale.order.line'].search([
                ('invoice_lines', 'in', self.invoice_line_ids.ids)
            ]).mapped('order_id')
            if not created_orders:
                order = self.env['sale.order'].create({
                    'opportunity_id': move.opportunity_id.id,
                    'partner_id': move.partner_id.id,
                    'campaign_id': move.campaign_id.id,
                    'medium_id': move.medium_id.id,
                    'origin': move.name,
                    'source_id': move.source_id.id,
                    'company_id': move.company_id.id or move.env.company.id,
                    'user_id': move.user_id.id,
                    'team_id': move.team_id.id,
                    'invoice_ids': [(4, move.id)],
                    'order_line': [
                        (0, 0, {
                            'product_id': line.product_id.id,
                            'product_uom_qty': line.quantity,
                            'price_unit': line.price_unit,
                            'tax_id': line.tax_ids.ids,
                            'invoice_lines': [(4, line.id)],
                        }) for line in move.invoice_line_ids]
                })
                if order:
                    template = self.env.ref('aznut_sale.confirm_invoice_from_opportunity_mail')
                    base_url = order.get_base_url()
                    menu_id = self.env.ref('sale.sale_menu_root').id
                    action_id = self.env.ref('sale.action_sale_order_form_view').id
                    secondary_url = 'web#id=%s&menu_id=%s&action=%s&model=sale.order&view_type=form' % (
                        order.id, menu_id, action_id
                    )
                    url = url_join(base_url, secondary_url)
                    if template:
                        template.with_context(order_url=url, invoice_name=move.display_name).sudo().send_mail(
                            order.id,
                            notif_layout='mail.mail_notification_light',
                        )
        return res
