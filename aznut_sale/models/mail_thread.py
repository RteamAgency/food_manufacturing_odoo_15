from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_add_suggested_recipient(self, result, partner=None, email=None, reason=''):
        return super(MailThread, self.sudo())._message_add_suggested_recipient(result, partner, email, reason)

    def _message_auto_subscribe(self, updated_values, followers_existing_policy='skip'):
        if not self:
            return True

        new_partner_subtypes = dict()

        updated_relation = dict()
        child_ids, def_ids, all_int_ids, parent, relation = self.env[
            'mail.message.subtype']._get_auto_subscription_subtypes(self._name)

        for res_model, fnames in relation.items():
            for field in (fname for fname in fnames if updated_values.get(fname)):
                updated_relation.setdefault(res_model, set()).add(field)
        udpated_fields = [fname for fnames in updated_relation.values() for fname in fnames if
                          updated_values.get(fname)]

        if udpated_fields:
            doc_data = [(model, [updated_values[fname] for fname in fnames]) for model, fnames in
                        updated_relation.items()]
            res = self.env['mail.followers']._get_subscription_data(doc_data, None, include_pshare=True,
                                                                    include_active=True)
            for _fol_id, _res_id, partner_id, subtype_ids, pshare, active in res:
                sids = [parent[sid] for sid in subtype_ids if parent.get(sid)]
                sids += [sid for sid in subtype_ids if sid not in parent and sid in child_ids]
                if partner_id and active:  # auto subscribe only active partners
                    if pshare:  # remove internal subtypes for customers
                        new_partner_subtypes[partner_id] = set(sids) - set(all_int_ids)
                    else:
                        new_partner_subtypes[partner_id] = set(sids)

        notify_data = dict()
        res = self._message_auto_subscribe_followers(updated_values, def_ids)
        for partner_id, sids, template in res:
            new_partner_subtypes.setdefault(partner_id, sids)
            if template:
                partner = self.env['res.partner'].browse(partner_id)
                lang = partner.sudo().lang if partner else None
                notify_data.setdefault((template, lang), list()).append(partner_id)
        self.env['mail.followers']._insert_followers(
            self._name, self.ids,
            list(new_partner_subtypes), subtypes=new_partner_subtypes,
            check_existing=True, existing_policy=followers_existing_policy)

        for (template, lang), pids in notify_data.items():
            self.with_context(lang=lang)._message_auto_subscribe_notify(pids, template)

        return True
