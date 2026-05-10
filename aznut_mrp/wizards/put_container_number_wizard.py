from odoo import fields, models
from odoo.exceptions import ValidationError

from num2words import num2words
from string import ascii_uppercase, digits
from random import choices


def generate_barcode_code(length=10):
    chars = ascii_uppercase + digits
    return ''.join(choices(chars, k=length))


def is_within_range(value):
    max_int = 2147483647
    return value <= max_int


class PutContainerNumberWizard(models.TransientModel):
    _name = 'put.container.number.wizard'
    _description = 'Put Container Number Wizard'

    premix_quality_check_line_id = fields.Many2one(
        'quality.check.premix.line',
        string='Premix Quality Check Line',
        required=True,
    )
    container_number = fields.Integer(
        string='Container Number',
        readonly=True,
    )

    def get_reload_values(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Put Container Number',
            'view_mode': 'form',
            'res_model': 'put.container.number.wizard',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context,
        }

    def set_number(self):
        self.ensure_one()
        number = self.env.context.get('number', None)
        if number is not None:
            number = int(str(self.container_number) + str(number))
            if is_within_range(number):
                self.container_number = number
            else:
                raise ValidationError('Value Exceeds The Integer Range!')
        return self.get_reload_values()

    def delete_number(self):
        self.ensure_one()
        if self.container_number:
            string_container_number = str(self.container_number)[0:-1]
            if string_container_number:
                self.container_number = int(string_container_number)
            else:
                self.container_number = 0
        return self.get_reload_values()

    def confirm_number(self):
        self.ensure_one()
        if not self.container_number:
            raise ValidationError('Value Must Be Greater Than 0!')
        self.premix_quality_check_line_id.write({'container_number': self.container_number})
        return self.env['quality.check'].with_context(workorder_id=self.premix_quality_check_line_id.quality_check_id.workorder_id.id).action_return_to_the_production_workorder()
