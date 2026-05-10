from odoo import models


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def __getitem__(self, key):
        if isinstance(key, str):
            if key == 'message_partner_ids' and self._name == 'account.reconcile.model':
                return self._fields[key].__get__(self.sudo(), self.env.registry[self._name])
            if key == 'member_ids' and self._name == 'crm.team':
                return self._fields[key].__get__(self.sudo(), self.env.registry[self._name])
            if key == 'last_working_user_id' and self._name == 'mrp.workorder':
                return self._fields[key].__get__(self.sudo(), self.env.registry[self._name])
            return self._fields[key].__get__(self, self.env.registry[self._name])
        elif isinstance(key, slice):
            return self.browse(self._ids[key])
        else:
            return self.browse((self._ids[key],))
