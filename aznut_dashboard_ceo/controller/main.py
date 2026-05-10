from odoo import http, fields
from odoo.http import request
from collections import defaultdict
import datetime
import re


def prepare_block_data(target_list, data, title=None, action_class=None, color=None, chart_id=None, res_ids=None):
    block = {
        **({'data': data} if data else {}),
        **({'title': title} if title else {}),
        **({'action_class': action_class} if action_class else {}),
        **({'chart_id': chart_id} if chart_id else {}),
        **({'color': color} if color else {}),
        **({'res_ids': res_ids} if res_ids else {}),
    }
    target_list.append(block)

def format_number(n):
    return f"{n:,.2f}"

class DashboardCEO(http.Controller):
    
    @http.route('/ceo_dashboard/get_data', auth='user', type='json')
    def get_blocks_data(self):
        dashboard_blocks = {}
        dashboard_blocks.update(self.get_sale_blocks_data())
        dashboard_blocks.update(self.get_production_blocks_data())
        dashboard_blocks.update(self.get_purchase_blocks_data())
        dashboard_blocks.update(self.get_crm_blocks_data())
        dashboard_blocks.update(self.get_inventory_blocks_data())
        dashboard_blocks.update(self.get_packaging_blocks_data())
        return dashboard_blocks

    def get_sale_blocks_data(self):
        current_date = datetime.datetime.now()
        start_of_month = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_year = current_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        sale_blocks = {
            'sales_simple': [],
            'sales_diagram':[]
        }

        qty_m, total_m, profit_m = self.get_so_period_stats(start_of_month, current_date)
        qty_y, total_y, profit_y = self.get_so_period_stats(start_of_year, current_date)
        so_chart_month = self.get_so_stats_grouped_by_brand(start_of_month, current_date)
        so_chart_year = self.get_so_stats_grouped_by_brand(start_of_year, current_date)
        
        prepare_block_data(sale_blocks['sales_simple'], [f"{qty_m} Jr", f"{total_m} $"], title='Ordered this month')
        prepare_block_data(sale_blocks['sales_simple'], [f"{qty_y} Jr", f"{total_y} $"], title='Ordered this year')
        prepare_block_data(sale_blocks['sales_simple'], [f"{profit_m} %"], title='Profit this month')
        prepare_block_data(sale_blocks['sales_simple'], [f"{profit_y} %"], title='Profit this year')
        
        prepare_block_data(sale_blocks['sales_diagram'], so_chart_month, title='Month', chart_id='month')
        prepare_block_data(sale_blocks['sales_diagram'], so_chart_year, title='Year', chart_id='year')
        return sale_blocks
    
    def combine_so_stats(self, so_chart_month, so_chart_year):
        stats = defaultdict(lambda: {
            'qty_month': 0,
            'qty_year': 0,
            'amount_month': 0,
            'amount_year': 0,
        })

        for brand, qty, amount in so_chart_month:
            stats[brand]['qty_month'] = qty
            stats[brand]['amount_month'] = amount

        for brand, qty, amount in so_chart_year:
            stats[brand]['qty_year'] = qty
            stats[brand]['amount_year'] = amount

        def sort_key(item):
            brand = item[0]
            return '' if brand is None else brand.lower()

        qty_chart = [(brand, data['qty_month'], data['qty_year']) for brand, data in sorted(stats.items(), key=sort_key)]
        amount_chart = [(brand, data['amount_month'], data['amount_year']) for brand, data in sorted(stats.items(), key=sort_key)]

        return qty_chart, amount_chart

    def get_production_blocks_data(self):
        current_date = datetime.datetime.now()
        start_of_month = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_year = current_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        mo_blocks = {
            'production_simple': [],
            'schedule_orders': [],
        }
                
        qty_month, batches_month = self.get_mo_period_stats(start_of_month, current_date)
        qty_year, batches_year = self.get_mo_period_stats(start_of_year, current_date)
        
        prepare_block_data(mo_blocks['production_simple'], [f"{qty_month} Jr", f"{batches_month} B"], title='Produced this month')
        prepare_block_data(mo_blocks['production_simple'], [f"{qty_year} Jr", f"{batches_year} B"], title='Produced this year')
        
        for days_left in range(7, 0, -1):
            target_date = fields.Date.today() + datetime.timedelta(days=days_left)
            start_of_day = datetime.datetime.combine(target_date, datetime.time.min)
            end_of_day = datetime.datetime.combine(target_date, datetime.time.max)
            mos = request.env['mrp.production'].search([
                ('date_planned_start', '>=', start_of_day),
                ('date_planned_start', '<=', end_of_day),
                ('state', 'not in', ['draft', 'done', 'cancel'])
            ])
            prepare_block_data(mo_blocks['schedule_orders'], [len(mos)], title=f'{days_left} days', color="stat-red" if days_left in [1,2,3] else False, action_class='schedule_mo', res_ids=mos.ids)

        end_today = datetime.datetime.combine(fields.Date.today(), datetime.time.max)

        overdue_mos = request.env['mrp.production'].search([
            ('date_planned_start', '<=', end_today),
            ('state', 'not in', ['draft', 'done', 'cancel']),
        ])
        prepare_block_data(mo_blocks['schedule_orders'], [len(overdue_mos)], title='Overdue', color="stat-red", action_class='schedule_mo', res_ids=overdue_mos.ids)
        return mo_blocks
    
    def get_purchase_blocks_data(self):
        po_dashboard_data = request.env['purchase.order'].retrieve_dashboard()
        current_date = datetime.datetime.now()
        start_of_month = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        yesterday =  (current_date - datetime.timedelta(days=1)).date()
        start_of_yesterday = datetime.datetime.combine(yesterday, datetime.time.min)
        end_of_yesterday = datetime.datetime.combine(yesterday, datetime.time.max)
        mo_blocks = {
            'batch_availability': [],
            'batch_records_15_min': [],
        }
        
        count_yesterday, batch_yesteday = self.get_production_batch_count(start_of_yesterday, end_of_yesterday)
        count_monthly, batch_monthly = self.get_production_batch_count(start_of_month, current_date)
        
        prepare_block_data(mo_blocks['batch_availability'], [f"{po_dashboard_data.get('available_batches')}"], title='Available')
        prepare_block_data(mo_blocks['batch_availability'], [f"{po_dashboard_data.get('not_available_batches')}"], title='Not Available', action_class='not_available_components')
        
        prepare_block_data(mo_blocks['batch_records_15_min'], [str(count_yesterday)], title='Yesterday', action_class='yesterday_15_min', res_ids=batch_yesteday)
        prepare_block_data(mo_blocks['batch_records_15_min'], [str(count_monthly)], title='This Month', action_class='month_15_min', res_ids=batch_monthly)
    
        return mo_blocks

    def get_crm_blocks_data(self):
        crm_blocks = {
            'customer_answers': [],
        }
        waiting_count, waiting_ids = self.get_crm_waiting_count()
        urgent_activities = request.env['mail.activity'].search([
            ('importance_level', '=', 'urgent'),
        ])
        prepare_block_data(crm_blocks['customer_answers'], [waiting_count], title='Customers without answers', action_class='waiting_leads', res_ids=waiting_ids)
        prepare_block_data(crm_blocks['customer_answers'], [len(urgent_activities)], title='Urgent activities', action_class='urgent_activities', res_ids=urgent_activities.ids)
        return crm_blocks

    def get_inventory_blocks_data(self):
        inventory_blocks = {
            'inventory_simple': [],
        }
        stock_cost = self.get_inventory_on_hand_cost()
        open_invoice_amount, res_ids = self.get_open_invoice_amount()
        
        prepare_block_data(inventory_blocks['inventory_simple'], [f"{stock_cost} $"], title='Value')
        prepare_block_data(inventory_blocks['inventory_simple'], [f"{open_invoice_amount} $"], title='Open invoices', action_class='open_inv', res_ids=res_ids)
        return inventory_blocks

    def get_packaging_blocks_data(self):
        packaging_blocks = {
            'packaging_simple': [],
        }
        current_date = datetime.datetime.now()
        start_of_month = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        yesterday =  (current_date - datetime.timedelta(days=1)).date()
        start_of_yesterday = datetime.datetime.combine(yesterday, datetime.time.min)
        end_of_yesterday = datetime.datetime.combine(yesterday, datetime.time.max)
        
        yesterday_packaging = self.get_packaging_stats(start_of_yesterday, end_of_yesterday)
        month_packaging = self.get_packaging_stats(start_of_month, current_date)
        
        prepare_block_data(packaging_blocks['packaging_simple'], [f"{yesterday_packaging[0]} Jr", f"{yesterday_packaging[1]}"], title='Packaged Jars')
        prepare_block_data(packaging_blocks['packaging_simple'], [f"{month_packaging[0]} Jr", f"{month_packaging[1]}"], title='Packaged Jars this Month')
        return packaging_blocks



    def get_so_stats_grouped_by_brand(self, start_date, end_date):
        query = """
            SELECT
                pav.name AS brand_name,
                COALESCE(SUM(sol.product_uom_qty), 0) AS total_qty,
                COALESCE(SUM(so.amount_total), 0) AS total_amount
            FROM sale_order so
            LEFT JOIN sale_order_line sol ON sol.order_id = so.id
            LEFT JOIN product_product pp ON sol.product_id = pp.id
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN product_template_attribute_value ptav ON ptav.product_tmpl_id = pt.id
            LEFT JOIN product_attribute pa ON ptav.attribute_id = pa.id AND pa.name = 'Brand'
            LEFT JOIN product_attribute_value pav ON ptav.product_attribute_value_id = pav.id
            WHERE so.create_date >= %s AND so.create_date <= %s
            GROUP BY pav.name
            ORDER BY pav.name
        """
        request.env.cr.execute(query, (start_date, end_date))
        return request.env.cr.fetchall()
    
    def get_so_period_stats(self, start_date, end_date):
        query = """
            SELECT
                COALESCE(SUM(sol.product_uom_qty), 0) AS total_qty,
                COALESCE(SUM(so.amount_total), 0) AS total_amount,
                COALESCE(SUM(
                    CASE WHEN so.show_production_margin THEN so.production_margin ELSE 0 END
                ), 0) AS total_margin,
                COALESCE(SUM(
                    CASE WHEN so.show_production_margin THEN so.amount_untaxed ELSE 0 END
                ), 0) AS total_untaxed
            FROM sale_order so
            LEFT JOIN sale_order_line sol ON sol.order_id = so.id
            WHERE so.create_date >= %s AND so.create_date <= %s
        """
        request.env.cr.execute(query, (start_date, end_date))
        result = request.env.cr.fetchone()
        total_qty, total_amount, total_margin, total_untaxed = result
        profit_percent = (total_margin / total_untaxed * 100) if total_untaxed else 0
        return format_number(total_qty), format_number(total_amount), format_number(round(profit_percent, 2))
        
    def get_mo_period_stats(self, start_date, end_date):
        query = """
            SELECT
                COALESCE(SUM(product_qty), 0) AS total_qty,
                COALESCE(SUM(FLOOR(product_qty / NULLIF(product_template.batch, 0))::INTEGER), 0) AS total_batches
            FROM mrp_production
            JOIN product_product ON product_product.id = mrp_production.product_id
            JOIN product_template ON product_template.id = product_product.product_tmpl_id
            WHERE date_finished BETWEEN %s AND %s
        """
        request.env.cr.execute(query, (start_date, end_date))
        result = request.env.cr.fetchone()
        return format_number(result[0]), format_number(result[1])

    def get_production_batch_count(self, start_date, end_date):
        query = """
            SELECT COUNT(batch.id), ARRAY_AGG(batch.id)
            FROM mrp_workorder wo
            JOIN mrp_workcenter wc ON wo.workcenter_id = wc.id
            JOIN mrp_workorder_batch batch ON batch.workorder_id = wo.id
            WHERE wo.date_finished BETWEEN %s AND %s
                AND wc.production_station IS TRUE
                AND batch.time_start IS NOT NULL
                AND batch.time_finish IS NOT NULL
                AND EXTRACT(EPOCH FROM (batch.time_finish - batch.time_start)) / 60 >= 15
        """
        request.env.cr.execute(query, (start_date, end_date))
        count, batch_ids = request.env.cr.fetchone()
        return count, batch_ids
    
    def get_inventory_on_hand_cost(self):
        query = """
            SELECT SUM(sq.quantity * irp.value_float) AS total_value
            FROM stock_quant sq
            JOIN stock_location sl ON sq.location_id = sl.id
            JOIN product_product pp ON sq.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN ir_property irp
                ON irp.name = 'standard_price'
                AND irp.res_id = CONCAT('product.product,', pp.id)
            WHERE pt.purchase_ok = TRUE
                AND sl.usage = 'internal';
        """
        request.env.cr.execute(query,)
        return format_number(request.env.cr.fetchone()[0]) or 0
    
    def get_open_invoice_amount(self):
        query = """
            SELECT
                SUM(am.amount_total) AS total_amount,
                ARRAY_AGG(DISTINCT am.id) AS move_ids
            FROM sale_order so
            JOIN sale_order_line sol ON sol.order_id = so.id
            JOIN sale_order_line_invoice_rel solir ON solir.order_line_id = sol.id
            JOIN account_move_line aml ON aml.id = solir.invoice_line_id
            JOIN account_move am ON am.id = aml.move_id
            WHERE so.payment_status IN ('partially_paid', 'waiting')
            AND am.move_type IN ('out_invoice', 'out_refund')
        """
        request.env.cr.execute(query,)
        result = request.env.cr.fetchone()
        amount_total = result[0] or 0
        move_ids = result[1] or []
        return format_number(amount_total), move_ids
    
    def get_packaging_stats(self, start_date, end_date):
        query="""
            SELECT
                COALESCE(SUM(w.qty_produced), 0) AS qty_produced_month,
                COALESCE(SUM(w.duration), 0) AS time_produced_month
            FROM mrp_workorder w
            JOIN mrp_workcenter wc ON wc.id = w.workcenter_id
            WHERE w.date_finished BETWEEN %s AND %s
                AND wc.packaging_station IS TRUE;
        """
        request.env.cr.execute(query, (start_date, end_date))
        result = request.env.cr.fetchone()
        return format_number(result[0]), round(result[1], 2)
    
    def get_crm_waiting_count(self):
        Lead = request.env['crm.lead'].sudo()
        two_weeks_ago = datetime.datetime.now() - datetime.timedelta(days=14)
        leads = Lead.search([
            ('email_from', '!=', False),
        ])
        leads = leads.filtered(lambda rec: rec.stage_id.name != 'No Respond')
        waiting_ids = []

        for lead in leads:
            messages = request.env['mail.message'].sudo().search([
                ('model', '=', 'crm.lead'),
                ('res_id', '=', lead.id),
                ('date', '>=', two_weeks_ago.strftime('%Y-%m-%d %H:%M:%S'))
            ], order='date ASC')

            if not messages:
                continue
            
            last_from_partner = None
            for msg in reversed(messages):
                if msg.email_from and lead.email_from.lower() in msg.email_from.lower():
                    last_from_partner = msg
                    break

            if not last_from_partner:
                continue
            
            after_reply_from_us = any(
                msg.date > last_from_partner.date and
                msg.email_from and lead.email_from.lower() not in msg.email_from.lower()
                for msg in messages
            )

            if not after_reply_from_us:
                waiting_ids.append(lead.id)

        return len(waiting_ids), waiting_ids
