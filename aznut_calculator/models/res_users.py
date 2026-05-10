from odoo import api, models
from odoo.exceptions import ValidationError


class Users(models.Model):
    _inherit = "res.users"

    @api.constrains('groups_id')
    def _check_one_user_type(self):
        super(Users, self)._check_one_user_type()

        conflict_sets = [
            (
                ['aznut_calculator.group_calculator_procurement',
                 'aznut_calculator.group_calculator_user'],
                "A user cannot have both Calculator Procurement and Calculator User/Manager/Administrator."
            ),
            (
                ['aznut_calculator.group_calculator_salesperson',
                 'aznut_calculator.group_calculator_manager'],
                "A user cannot have both Calculator Salesperson and Calculator Manager/Administrator."
            ),
            (
                ['aznut_calculator.group_calculator_salesperson',
                 'aznut_sale.group_contacts_user'],
                "A user cannot have both Calculator Salesperson and Contacts User/Administrator."
            ),
        ]

        for user in self:
            for group_xml_ids, error_message in conflict_sets:
                group_ids = [
                    self.env.ref(xml_id, False).id
                    for xml_id in group_xml_ids
                    if self.env.ref(xml_id, False)
                ]

                if len(group_ids) < 2:
                    continue

                if user._has_multiple_groups(group_ids):
                    raise ValidationError(error_message)
