from odoo import models, api, fields, _
from datetime import date, timedelta
from odoo.tools import float_compare, format_date


class ReportBomStructure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    @api.model
    def _get_quantities_info(self, product, bom_uom):
        return {
            'free_qty': product.uom_id._compute_quantity(product.free_qty,
                                                         bom_uom) if product.detailed_type == 'product' else False,
            'on_hand_qty': product.uom_id._compute_quantity(product.qty_available,
                                                            bom_uom) if product.detailed_type == 'product' else False,
            'stock_loc': 'in_stock',

        }

    @api.model
    def _get_stock_availability(self, product, quantity, product_info, quantities_info, bom_line=None):
        closest_forecasted = None
        if bom_line:
            closest_forecasted = self.env.context.get('components_closest_forecasted', {}).get(product.id, {}).get(
                bom_line.id)
        if closest_forecasted == date.min:
            return ('available', 0)
        if closest_forecasted == date.max:
            return ('unavailable', False)
        date_today = self.env.context.get('from_date', fields.date.today())
        if product.detailed_type != 'product':
            return ('available', 0)

        stock_loc = quantities_info['stock_loc']
        product_info[product.id]['consumptions'][stock_loc] += quantity
        if float_compare(product_info[product.id]['consumptions'][stock_loc], quantities_info['free_qty'],
                         precision_rounding=product.uom_id.rounding) <= 0:
            return ('available', 0)

        if stock_loc == 'in_stock':
            domain = [('state', '=', 'forecast'), ('date', '>=', date_today), ('product_id', '=', product.id),
                      ('product_qty', '>=', product_info[product.id]['consumptions'][stock_loc])]
            if self.env.context.get('warehouse'):
                domain.append(('warehouse_id', '=', self.env.context.get('warehouse')))

            if not closest_forecasted:
                closest_forecasted = self.env['report.stock.quantity'].read_group(domain,
                                                                                  ['min_date:min(date)', 'product_id'],
                                                                                  ['product_id'])
                closest_forecasted = closest_forecasted and closest_forecasted[0]['min_date']
            if closest_forecasted:
                days_to_forecast = (closest_forecasted - date_today).days
                return ('expected', days_to_forecast)
        return ('unavailable', False)

    @api.model
    def _get_resupply_availability(self, route_info, components):
        if route_info.get('route_type') == 'manufacture':
            max_component_delay = self._get_max_component_delay(components)
            if max_component_delay is False:
                return ('unavailable', False)
            produce_delay = route_info.get('manufacture_delay', 0) + max_component_delay
            return ('estimated', produce_delay)
        return ('unavailable', False)

    @api.model
    def _get_max_component_delay(self, components):
        max_component_delay = 0
        for component in components:
            line_delay = component.get('availability_delay', False)
            if line_delay is False:
                return False
            max_component_delay = max(max_component_delay, line_delay)
        return max_component_delay

    @api.model
    def _get_availabilities(self, product, quantity, product_info, bom_key, quantities_info,
                            components=False, bom_line=None):

        stock_state, stock_delay = self._get_stock_availability(product, quantity, product_info, quantities_info,
                                                                bom_line=bom_line)

        components = components or []
        route_info = product_info[product.id].get(bom_key)
        resupply_state, resupply_delay = ('unavailable', False)
        if product.detailed_type != 'product':
            resupply_state, resupply_delay = ('available', 0)
        elif route_info:
            resupply_state, resupply_delay = self._get_resupply_availability(route_info, components)

        base = {
            'resupply_avail_delay': resupply_delay,
            'stock_avail_state': stock_state,
        }
        if stock_state != 'unavailable':
            return {**base, **{
                'availability_display': self._format_date_display(stock_state, stock_delay),
                'availability_state': stock_state,
                'availability_delay': stock_delay,
            }}
        return {**base, **{
            'availability_display': self._format_date_display(resupply_state, resupply_delay),
            'availability_state': resupply_state,
            'availability_delay': resupply_delay,
        }}

    @api.model
    def _update_product_info(self, product, bom_key, product_info, warehouse, quantity, bom, parent_bom):
        key = product.id
        if key not in product_info:
            product_info[key] = {'consumptions': {'in_stock': 0}}
        if not product_info[key].get(bom_key):
            product_info[key][bom_key] = self.with_context(
                product_info=product_info, parent_bom=parent_bom
            )._get_resupply_route_info(warehouse, product, quantity, bom)

    @api.model
    def _format_route_info(self, rules, rules_delay, warehouse, product, bom, quantity):
        manufacture_rules = [rule for rule in rules if rule.action == 'manufacture' and bom]
        if manufacture_rules:
            wh_manufacture_rules = product._get_rules_from_location(product.property_stock_production,
                                                                    route_ids=warehouse.route_ids)
            wh_manufacture_rules -= rules
            rules_delay += sum(rule.delay for rule in wh_manufacture_rules)
            manufacturing_lead = bom.company_id.manufacturing_lead if bom and bom.company_id else 0
            return {
                'route_type': 'manufacture',
                'route_name': manufacture_rules[0].route_id.display_name,
                'route_detail': bom.display_name,
                'lead_time': product.produce_delay + rules_delay + manufacturing_lead,
                'manufacture_delay': product.produce_delay + rules_delay + manufacturing_lead,
            }
        return {}

    @api.model
    def _get_resupply_route_info(self, warehouse, product, quantity, bom=False):
        found_rules = []
        if not found_rules:
            found_rules = product._get_rules_from_location(warehouse.lot_stock_id)
        if not found_rules:
            return {}
        rules_delay = sum(rule.delay for rule in found_rules)
        return self._format_route_info(found_rules, rules_delay, warehouse, product, bom, quantity)

    @api.model
    def get_warehouses(self):
        return self.env['stock.warehouse'].search_read([('company_id', 'in', self.env.companies.ids)],
                                                       fields=['id', 'name'])

    @api.model
    def _format_date_display(self, state, delay):
        date_today = self.env.context.get('from_date', fields.date.today())
        if state == 'available':
            return _('Available')
        if state == 'unavailable':
            return _('Not Available')
        if state == 'expected':
            return _('Expected %s', format_date(self.env, date_today + timedelta(days=delay)))
        if state == 'estimated':
            return _('Estimated %s', format_date(self.env, date_today + timedelta(days=delay)))
        return ''
