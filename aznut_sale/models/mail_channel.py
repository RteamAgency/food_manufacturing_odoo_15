from odoo import models


class MailChannel(models.Model):
    _inherit = 'mail.channel'

    def _broadcast(self, partner_ids):
        notifications = self.sudo()._channel_channel_notifications(partner_ids)
        self.env['bus.bus']._sendmany(notifications)
