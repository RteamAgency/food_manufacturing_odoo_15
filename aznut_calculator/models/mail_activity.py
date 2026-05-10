from odoo import models


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def _action_done(self, feedback=False, attachment_ids=False):
        return super(MailActivity, self.with_context(activity_mail=True))._action_done(feedback, attachment_ids)
