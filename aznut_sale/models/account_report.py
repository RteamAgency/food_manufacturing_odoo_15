from odoo import models, api

from odoo.tools.misc import formatLang, format_date


class AnalyticReport(models.AbstractModel):
    _inherit = 'account.analytic.report'

    def _generate_analytic_account_lines(self, analytic_accounts, parent_id=False):
        lines = []

        for account in analytic_accounts:
            lines.append({
                'id': 'analytic_account_%s' % account.id,
                'name': account.name,
                'columns': [{'name': account.code},
                            {'name': account.partner_id.sudo().display_name},
                            {'name': self.format_value(account.balance)}],
                'level': 4,
                'unfoldable': False,
                'caret_options': 'account.analytic.account',
                'parent_id': parent_id,
            })

        return lines


class AccountReconciliation(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    @api.model
    def _prepare_move_lines(self, move_lines, target_currency=False, target_date=False, recs_count=0):
        ret = []

        for line in move_lines:
            company_currency = line.company_id.currency_id
            line_currency = (line.currency_id and line.amount_currency) and line.currency_id or company_currency
            ret_line = {
                'id': line.id,
                'name': line.name and line.name != '/' and line.move_id.name != line.name and line.move_id.name + ': ' + line.name or line.move_id.name,
                'ref': line.move_id.ref or '',
                'account_id': [line.account_id.id, line.account_id.display_name],
                'is_liquidity_line': line.account_id.internal_type == 'liquidity',
                'account_code': line.account_id.code,
                'account_name': line.account_id.name,
                'account_type': line.account_id.internal_type,
                'date_maturity': format_date(self.env, line.date_maturity),
                'date': format_date(self.env, line.date),
                'journal_id': [line.journal_id.id, line.journal_id.display_name],
                'partner_id': line.partner_id.id,
                'partner_name': line.partner_id.sudo().name,
                'currency_id': line_currency.id,
            }

            debit = line.debit
            credit = line.credit
            amount = line.amount_residual
            amount_currency = line.amount_residual_currency

            if line.account_id.internal_type == 'liquidity':
                amount = debit - credit
                amount_currency = line.amount_currency

            target_currency = target_currency or company_currency

            if target_currency == company_currency:
                if line_currency == target_currency:
                    amount = amount
                    amount_currency = ""
                    total_amount = debit - credit
                    total_amount_currency = ""
                else:
                    amount = amount
                    amount_currency = amount_currency
                    total_amount = debit - credit
                    total_amount_currency = line.amount_currency

            if target_currency != company_currency:
                if line_currency == target_currency:
                    amount = amount_currency
                    amount_currency = ""
                    total_amount = line.amount_currency
                    total_amount_currency = ""
                else:
                    amount_currency = line.currency_id and amount_currency or amount
                    company = line.account_id.company_id
                    date = target_date or line.date
                    amount = company_currency._convert(amount, target_currency, company, date)
                    total_amount = company_currency._convert((line.debit - line.credit), target_currency, company, date)
                    total_amount_currency = line.currency_id and line.amount_currency or (line.debit - line.credit)

            ret_line['recs_count'] = recs_count
            ret_line['debit'] = amount > 0 and amount or 0
            ret_line['credit'] = amount < 0 and -amount or 0
            ret_line['amount_currency'] = amount_currency
            ret_line['amount_str'] = formatLang(self.env, abs(amount), currency_obj=target_currency)
            ret_line['total_amount_str'] = formatLang(self.env, abs(total_amount), currency_obj=target_currency)
            ret_line['amount_currency_str'] = amount_currency and formatLang(self.env, abs(amount_currency),
                                                                             currency_obj=line_currency) or ""
            ret_line['total_amount_currency_str'] = total_amount_currency and formatLang(self.env,
                                                                                         abs(total_amount_currency),
                                                                                         currency_obj=line_currency) or ""
            ret.append(ret_line)
        return ret
