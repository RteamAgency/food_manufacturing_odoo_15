################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2019 SmartTek (<https://smartteksas.com/>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
################################################################################

from . import models
from . import wizard

from odoo import _

from odoo.addons.project.models.project import Task
from odoo.addons.product.models.product import ProductProduct


def post_load_hook():
    def _message_get_suggested_recipients(self):
        recipients = super(Task, self)._message_get_suggested_recipients()
        for task in self:
            if task.partner_id:
                reason = _('Customer Email') if task.sudo().partner_id.email else _('Customer')
                task._message_add_suggested_recipient(recipients, partner=task.sudo().partner_id, reason=reason)
            elif task.email_from:
                task._message_add_suggested_recipient(recipients, email=task.email_from, reason=_('Customer Email'))
        return recipients

    def _prepare_sellers(self, params=False):
        return self.seller_ids.sudo().filtered(lambda s: s.name.active).sorted(
            lambda s: (s.sequence, -s.min_qty, s.price, s.id)
        )

    Task._message_get_suggested_recipients = _message_get_suggested_recipients
    ProductProduct._prepare_sellers = _prepare_sellers
