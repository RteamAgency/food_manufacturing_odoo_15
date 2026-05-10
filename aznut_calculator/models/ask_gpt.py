from odoo import fields, models, api
from odoo.exceptions import ValidationError

from json import loads, JSONDecodeError, dumps
from openai import OpenAI
from datetime import datetime
from emoji import replace_emoji

CHAT_TEMPLATE = """
    <div class='aznut-calculator-chat-container'>
        %s
    </div>
"""

ROLES_CLASSES = {
    "system": "aznut-calculator-message aznut-calculator-message-system",
    "user": "aznut-calculator-message aznut-calculator-message-user",
    "assistant": "aznut-calculator-message aznut-calculator-message-assistant"
}


def remove_emojis(text):
    return replace_emoji(text, replace='')


def get_ingredients(ingredients, product_field, quantity_field, uom_field):
    if product_field in ingredients._fields and quantity_field in ingredients._fields and uom_field in ingredients._fields:
        return list(
            map(lambda ing: '%s - %s %s' % (
                getattr(ing, product_field).name, "{:.4f}".format(getattr(ing, quantity_field)), getattr(ing, uom_field).name),
                ingredients))
    return []


def get_gpt_session_window(view_id, res_id):
    return {
        'name': 'Ask GPT Session',
        'type': 'ir.actions.act_window',
        'res_model': 'ask.gpt.session',
        'view_mode': 'form',
        'view_id': view_id,
        'target': 'new',
        'res_id': res_id,
    }


class AskGptSession(models.Model):
    _name = 'ask.gpt.session'
    _description = 'Ask GPT Session'

    history = fields.Text(
        string='History',
        copy=False,
        default='[]',

    )
    chat = fields.Html(
        string='Chat',
        compute='_compute_chat',
        default=CHAT_TEMPLATE % '',
    )
    user_input = fields.Text(
        string='Message',
        copy=False,
    )
    powder_calculator_id = fields.Many2one(
        'powder.calculator',
        string='Powder Calculator',
        readonly=True,
        copy=False,
    )
    product_calculator_id = fields.Many2one(
        'product.calculator',
        string='Product Calculator',
        readonly=True,
        copy=False,
    )
    name = fields.Char(
        string='Name',
        default='New',
        readonly=True,
    )

    @api.depends('history')
    def _compute_chat(self):
        self.chat = CHAT_TEMPLATE % ''
        for chat in self.filtered(lambda ct: ct.history):
            try:
                history = reversed(loads(chat.history))

                messages_html = ""
                for msg in history:
                    role = msg["role"]
                    content = msg["content"].replace("\n", "<br>")
                    time = msg.get("time", "")

                    messages_html += f"""
                        <div class='{ROLES_CLASSES.get(role, "aznut-calculator-message")}'>
                            <div class='aznut-calculator-bubble'>{content}</div>
                            <span class='aznut-calculator-time'>{time}</span>
                        </div>
                    """

                chat.chat = remove_emojis(CHAT_TEMPLATE % messages_html)
            except (JSONDecodeError, TypeError) as e:
                chat.chat = f"<div class='aznut-calculator-error'>Error processing chat history: {str(e)}</div>"

    def action_send_message(self):
        api_key = self.env.ref('aznut_calculator.support_settings_main').gpt_token
        if not api_key:
            raise ValidationError('No Token Provided!')

        if self.user_input:
            try:
                if not self.history:
                    self.history = "[]"
                history = loads(self.history)

                user_message = {
                    "role": "user",
                    "content": self.user_input,
                    "time": datetime.now().strftime("%d.%m.%Y %H:%M")
                }
                history.append(user_message)

                client = OpenAI(api_key=api_key)

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": msg["role"], "content": msg["content"]} for msg in history]
                )

                assistant_message = {
                    "role": "assistant",
                    "content": response.choices[0].message.content,
                    "time": datetime.now().strftime("%d.%m.%Y %H:%M")
                }
                history.append(assistant_message)
                self.write({
                    'history': dumps(history),
                    'user_input': False,
                })
            except JSONDecodeError:
                self.history = "[]"
        if self._context.get('from_calculator'):
            return get_gpt_session_window(self.env.ref('aznut_calculator.ask_gpt_session_form').id, self.id)

    def action_prefill(self):
        self.ensure_one()
        res = self.user_input or ''
        settings_text = self.env.ref('aznut_calculator.support_settings_main').gpt_text
        if settings_text:
            res += '\n%s' % settings_text
        calculator = self.product_calculator_id or self.powder_calculator_id
        if calculator:
            if calculator._name == 'product.calculator':
                active_ingredients = get_ingredients(calculator.active_ingredient_ids, 'product_id',
                                                     'quantity', 'active_ingredient_uom_id')
                if active_ingredients:
                    res += '\nActive Ingredients:\n%s' % '\n'.join(active_ingredients)
            elif calculator._name == 'powder.calculator':
                ingredients = get_ingredients(calculator.active_ingredient_ids, 'product_id', 'quantity', 'uom_id')
                if ingredients:
                    res += '\nIngredients:\n%s' % '\n'.join(ingredients)
        self.user_input = res
        if self._context.get('from_calculator'):
            return get_gpt_session_window(self.env.ref('aznut_calculator.ask_gpt_session_form').id, self.id)

    def action_clear(self):
        self.ensure_one()
        self.write({
            'history': '[]',
            'user_input': False,
        })
        if self._context.get('from_calculator'):
            return get_gpt_session_window(self.env.ref('aznut_calculator.ask_gpt_session_form').id, self.id)

    @api.model
    def create(self, vals):
        if 'name' not in vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('ask.gpt.session') or 'New'
        return super(AskGptSession, self).create(vals)
