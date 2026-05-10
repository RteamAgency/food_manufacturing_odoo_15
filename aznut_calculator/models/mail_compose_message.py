from odoo import models

from collections import defaultdict
from markupsafe import Markup

from .product_calculator import get_quantity_from_ingredient

TABLE_TEMPLATE = """
<h3>%s</h3>
<table class="table table-bordered">
    <thead>
        <tr>
            <th>Product</th>
            <th>Quantity</th>
            <th>UoM</th>
        </tr>
    </thead>
    <tbody>
        %s
    </tbody>
</table>
"""


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _action_send_mail(self, auto_commit=False):
        ing_ids = self.env.context.get('ing_ids')
        ing_model = self.env.context.get('ing_model')
        for wizard in self.filtered(lambda wzd: wzd.model in ['product.calculator', 'powder.calculator']):
            if ing_ids and ing_model:
                ingredients = self.env[ing_model].browse(ing_ids)
                vendors_dict = defaultdict(list)

                for ingredient in ingredients:
                    vendor_partners = ingredient.mapped('product_id.seller_ids.name')
                    for vendor in vendor_partners:
                        vendors_dict[vendor].append(ingredient)
                for vendor, values in vendors_dict.items():
                    tbody = ''
                    body = self.env.ref('aznut_calculator.support_settings_main').procurement_vendors_text
                    if '%name%' in body:
                        body = body.replace('%name%', vendor.name or '')
                    if '%ingredients%' in body:
                        for value in values:
                            quantity_field = 'readonly_quantity' if ing_model == 'active.ingredient' else 'total_bom_lb'
                            uom_field = 'uom_id' if ing_model == 'active.ingredient' else 'lb_uom_id'
                            quantity = get_quantity_from_ingredient(value, quantity_field)
                            tbody += f"""
                            <tr>
                                <td>{value.product_id.name or 'No Product'}</td>
                                <td>{round(quantity, 4)}</td>
                                <td>{getattr(value, uom_field).name or 'No UoM'}</td>
                            </tr>
                            """
                        if tbody:
                            table = TABLE_TEMPLATE % ('Ingredients', tbody)
                            body = body.replace('%ingredients%', Markup(table))
                    partners = (wizard.partner_ids - vendor.message_partner_ids) | vendor
                    self.env['mail.compose.message'].create({
                        'body': body,
                        'subject': 'Request For Ingredients',
                        'partner_ids': partners.ids,
                        'res_id': vendor.id,
                        'model': 'res.partner',
                    }).action_send_mail()
        return super(MailComposeMessage, self)._action_send_mail(auto_commit=auto_commit)
