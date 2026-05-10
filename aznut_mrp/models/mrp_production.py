################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2019 SmartTek (<https://smartteksas.com/>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
################################################################################

from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero, float_compare

from num2words import num2words
import pytz


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    @api.constrains('aznut_priority', 'date_planned_start')
    def _check_aznut_priority(self):
        for mo in self.filtered(lambda rec: rec.aznut_priority != '-1'):
            if mo.state != 'confirmed':
                raise ValidationError('Manufacturing order state must be confirmed!')

    production_cleaning_order_id = fields.Many2one(
        'mrp.production',
        string='Production Cleaning Order',
        copy=False,
    )
    packaging_cleaning_order_id = fields.Many2one(
        'mrp.production',
        string='Packaging Cleaning Order',
        copy=False,
    )

    store_picking_id = fields.Many2one(
        'stock.picking',
        string='Store Transfer',
        copy=False,
    )
    packaging_cleaning_date = fields.Date(
        string='Packaging Cleaning Date',
    )
    production_cleaning_date = fields.Date(
        string='Production Cleaning Date',
    )
    aznut_priority = fields.Selection(
        [('-1', 'No Priority'),('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')],
        string='Priority',
        group_expand='_expand_aznut_priority',
        compute='_compute_aznut_priority',
        store=True,
        readonly=False,
        default='-1',
        required=True,
    )
    is_quantity_confirmed = fields.Boolean(
        string='Is Quantity Confirmed',
    )
    mrp_color = fields.Selection(
        related='product_id.mrp_color',
    )
    is_lot_validated = fields.Boolean(
        string='Is Lot Validated',
    )
    parent_productions_ids = fields.Many2many(
        'mrp.production',
        'parent_productions_rel',
        'parent_production_id',
        compute='_compute_parent_productions_ids',
    )


    @api.depends('state')
    def _compute_aznut_priority(self):
        for mo in self:
            if mo.state == 'confirmed':
                mo.aznut_priority = mo.aznut_priority
            else:
                mo.aznut_priority = '-1'

    @api.depends(
        'move_raw_ids.state', 'move_raw_ids.quantity_done', 'move_finished_ids.state',
        'workorder_ids.state', 'product_qty', 'qty_producing')
    def _compute_state(self):
        for production in self:
            if not production.state or not production.product_uom_id:
                production.state = 'draft'
            elif production.state == 'cancel' or (production.move_finished_ids and all(
                    move.state == 'cancel' for move in production.move_finished_ids)):
                production.state = 'cancel'
            elif (
                    production.state == 'done'
                    or (production.move_raw_ids and all(
                move.state in ('cancel', 'done') for move in production.move_raw_ids))
                    and all(move.state in ('cancel', 'done') for move in production.move_finished_ids)
            ):
                production.state = 'done'
            elif production.workorder_ids and all(
                    wo_state in ('done', 'cancel') for wo_state in production.workorder_ids.mapped('state')):
                production.state = 'to_close'
            elif not production.workorder_ids and float_compare(production.qty_producing, production.product_qty,
                                                                precision_rounding=production.product_uom_id.rounding) >= 0:
                production.state = 'to_close'
            elif any(wo_state in ('progress', 'done') for wo_state in production.workorder_ids.mapped('state')):
                production.state = 'progress'
            elif any(not float_is_zero(move.quantity_done,
                                       precision_rounding=move.product_uom.rounding or move.product_id.uom_id.rounding)
                     for move in production.move_raw_ids if move.product_id):
                production.state = 'progress'

    def _compute_parent_productions_ids(self):
        self.parent_productions_ids = False
        for production in self:
            suitable_moves = production.move_raw_ids.filtered(
                lambda mv: mv.product_id.is_customer_specific_labeling
            )
            if suitable_moves:
                parent_productions = self.env['mrp.production']
                for mvl in suitable_moves.mapped('move_line_ids').filtered(lambda move_line: move_line.qty_done > 0):
                    parent_productions |= self.env['mrp.production'].search([
                        ('product_id', '=', mvl.product_id.id),
                        ('lot_producing_id', '=', mvl.lot_id.id),
                        ('state', '=', 'done'),
                    ])
                production.parent_productions_ids = parent_productions

    def _expand_aznut_priority(self, *args, **kwargs):
        return [key for key, val in self._fields['aznut_priority'].selection]

    def reserve_from_kanban(self, domain):
        mos = self.search(domain)
        sorted_mos = mos.sorted(key=lambda mo: (int(mo.aznut_priority), mo.batches_count, mo.create_date), reverse=True)
        sorted_mos.action_assign()

    def unreserve_from_kanban(self, domain):
        records = self.search(domain)
        records.do_unreserve()

    def _update_premix_checks(self):
        test = self.env.ref('mrp_workorder.test_type_register_consumed_materials').technical_name
        quality_check_domain = [('test_type', '=', test)]
        for production in self:
            premix_workorders = production.workorder_ids.filtered(
                lambda rec: rec.workcenter_id.premix_station and rec.state != 'done'
            )
            quality_check_domain.append(('workorder_id', 'in', premix_workorders.ids))
            quality_checks = self.env['quality.check'].search(quality_check_domain)
            for check in quality_checks:
                batches_count = production.batches_count or 1
                existing_check_lines = len(check.quality_check_premix_line_ids)
                if existing_check_lines == batches_count:
                    continue
                diff = batches_count - existing_check_lines
                if diff < 0:
                    check.quality_check_premix_line_ids.sorted('create_date')[:abs(diff)].unlink()
                else:
                    values = {
                        'quality_check_id': check.id,
                        'quantity': check.move_id.product_uom_qty / (check.production_id.batches_count or 1),
                    }
                    check.write({'quality_check_premix_line_ids': [(0, 0, values) for _ in range(diff)]})

    def _update_premix_lots(self):
        for production in self:
            premix_workorders = production.workorder_ids.filtered(
                lambda rec: rec.workcenter_id.premix_station and not rec.finished_lot_id
            )
            for workorder in premix_workorders[:1]:
                workorder.action_generate_serial()

    def _update_production_batches(self):
        for production in self:
            workorders = production.workorder_ids.filtered(
                lambda wo: wo.workcenter_id.production_station and wo.state != 'done'
            )

            for workorder in workorders:
                quality_checks = (workorder.check_ids | workorder.production_checks_ids).filtered(
                    lambda qc: qc.production_batches
                )
                workorder.write({'production_checks_ids': quality_checks.ids})
                quality_checks.filtered(lambda wo: wo.workorder_id).write({'workorder_id': False})
                if quality_checks:
                    prev_check = self.env['quality.check']
                    for check in workorder.check_ids:
                        check.previous_check_id = prev_check
                        prev_check.next_check_id = check
                        prev_check = check
                    workorder._change_quality_check('first')
                batch_size = workorder.product_id.batch
                batches_count = workorder.production_id.batches_count or 1

                existing_batches_len = len(workorder.workorder_batch_ids)
                example_batch = workorder.workorder_batch_ids[:1]
                example_check = workorder.workorder_batch_checks_ids.filtered(
                    lambda ch: not ch.production_check_id.not_create_components
                )[:1]

                if example_batch and example_check:
                    example_batch = example_batch[0]
                    example_check = example_check[0].production_check_id

                    example_lines = self.env['quality.check.production.line'].search([
                        ('workorder_batch_id', '=', example_batch.id),
                        ('quality_check_id', '=', example_check.id)
                    ])

                    if example_lines:
                        example_moves = workorder.production_id.move_raw_ids.filtered(
                            lambda mv: mv.bom_line_id and mv.bom_line_id.operation_id.workcenter_id.premix_station
                                       or not mv.bom_line_id
                        )
                        if len(example_moves) > len(example_lines):
                            product_list = [ln.component_id for ln in example_lines]
                            new_moves = self.env['stock.move']
                            for mv in example_moves:
                                if mv.product_id not in product_list:
                                    new_moves |= mv
                                else:
                                    product_list.pop(product_list.index(mv.product_id))
                            if new_moves:
                                for mv in new_moves:
                                    for batch in workorder.workorder_batch_ids:
                                        self.env['quality.check.production.line'].create({
                                            'quality_check_id': example_check.id,
                                            'component_id': mv.product_id.id,
                                            'quantity': round(mv.product_uom_qty / (production.batches_count or 1)),
                                            'workorder_batch_id': batch.id,
                                        })
                                current_quality_check_production_lines = self.env[
                                    'quality.check.production.line'].search([
                                    ('quality_check_id', '=', workorder.current_production_check_id.id),
                                    ('workorder_batch_id', '=', workorder.current_workorder_batch_id.id)
                                ])
                                workorder.write(
                                    {'current_production_check_lines_ids': current_quality_check_production_lines.ids})

                if batches_count == existing_batches_len:
                    continue

                workorder_vals = {}
                diff = batches_count - existing_batches_len
                mrp_workorder_batches = self.env['mrp.workorder.batch']
                batches_checks = self.env['mrp.workorder.batch.check']

                while workorder.current_quality_check_id.id in quality_checks.ids:
                    workorder._change_quality_check('next')

                if diff < 0:
                    existing_batches = workorder.workorder_batch_ids.sorted('create_date')[:abs(diff)]
                    for batch in existing_batches:
                        self.env['mrp.workorder.batch.check'].sudo().search([
                            ('workorder_batch_id', '=', batch.id),
                        ]).unlink()
                        self.env['quality.check.production.line'].sudo().search([
                            ('workorder_batch_id', '=', batch.id),
                        ]).unlink()
                        batch.unlink()
                else:
                    for i in range(diff):
                        batch_vals = {
                            'workorder_id': workorder.id,
                            'product_id': workorder.product_id.id,
                            'quantity': batch_size,
                            'name': '%s Batch' % num2words(i + 1, to='ordinal').capitalize()
                        }
                        mrp_workorder_batches |= self.env['mrp.workorder.batch'].create(batch_vals)

                    for check in quality_checks:
                        self.env['quality.check'].search([('next_check_id', '=', check.id)]).write({
                            'next_check_id': check.next_check_id.id
                        })
                        self.env['quality.check'].search([('previous_check_id', '=', check.id)]).write({
                            'previous_check_id': check.previous_check_id.id
                        })
                        if not check.not_create_components:
                            for batch in mrp_workorder_batches:
                                for move in workorder.production_id.move_raw_ids.filtered(
                                        lambda rec: rec.bom_line_id.operation_id.workcenter_id.premix_station or not rec.bom_line_id
                                ):
                                    self.env['quality.check.production.line'].sudo().create({
                                        'quality_check_id': check.id,
                                        'component_id': move.product_id.id,
                                        'quantity': round(move.product_uom_qty / (production.batches_count or 1)),
                                        'workorder_batch_id': batch.id
                                    })

                                batches_checks |= self.env['mrp.workorder.batch.check'].sudo().create({
                                    'workorder_batch_id': batch.id,
                                    'production_check_id': check.id,
                                })
                        else:
                            for workorder_batch in mrp_workorder_batches:
                                self.env['quality.check.production.line'].sudo().create({
                                    'quality_check_id': check.id,
                                    'workorder_batch_id': workorder_batch.id
                                })
                                batches_checks |= self.env['mrp.workorder.batch.check'].sudo().create({
                                    'workorder_batch_id': workorder_batch.id,
                                    'production_check_id': check.id,
                                })

                all_batches = workorder.workorder_batch_ids | mrp_workorder_batches
                all_batches_checks = batches_checks | workorder.workorder_batch_checks_ids
                current_check = quality_checks[:1]
                current_batch = all_batches[:1]
                current_quality_check_production_lines = self.env['quality.check.production.line'].search([
                    ('quality_check_id', '=', current_check.id),
                    ('workorder_batch_id', '=', current_batch.id)
                ])
                if workorder.production_status == 'none':
                    workorder_vals.update({'production_status': 'draft'})
                workorder_vals.update({
                    'workorder_batch_ids': all_batches.ids,
                    'current_workorder_batch_id': current_batch.id,
                    'current_production_check_id': current_check.id,
                    'current_production_check_lines_ids': current_quality_check_production_lines.ids,
                    'workorder_batch_checks_ids': all_batches_checks.ids,
                })
                workorder.write(workorder_vals)

    def action_confirm(self):
        self.move_raw_ids._fields['forecast_availability'].compute_value(self.move_raw_ids)
        res = super(MrpProduction, self).action_confirm()
        self._update_premix_lots()
        self._prepare_packaging()
        return res

    def _prepare_packaging(self):
        for production in self:
            packaging_wo = production.workorder_ids.filtered(lambda wo: wo.workcenter_id.packaging_station)[:1]
            if not packaging_wo:
                continue
            packaging_wo.write({
                'workorder_scrap_line_ids': [(0, 0, {
                    'product_id': mv.product_id.id,
                    'quantity': 1,
                    'uom_id': mv.product_id.uom_id.id,
                    'workorder_id': packaging_wo.id,
                }) for mv in packaging_wo.move_raw_ids]
            })
            activities = ['filling station', 'cap label station', 'ready product station']
            for activity in activities:
                packaging_activity = self.env['packaging.activity'].search([('name', '=ilike', activity)])
                if not packaging_activity:
                    packaging_activity = self.env['packaging.activity'].create({'name': activity.capitalize()})
                packaging_wo.packaging_activity_line_ids |= self.env['packaging.activity.line'].create({
                    'packaging_activity_id': packaging_activity.id
                })

    def _get_analyses_data(self):
        self.ensure_one()
        self = self.sudo()
        products = self.move_raw_ids.product_id
        workorders_operators = {}
        for workorder in self.workorder_ids:
            workorders_operators.update({workorder.name: ', '.join(workorder.mapped('done_employees_ids.name'))}
                                        )
        quality_check = []
        check_status = False
        worksheet_images = {}
        active_category = self.env['product.category'].search([('name', 'ilike', 'Active Ingredients')], limit=1)
        base_category = self.env['product.category'].search([('name', 'ilike', 'Base Ingredients')], limit=1)
        child_active_categories = self.env['product.category'].search([('id', 'child_of', active_category.id)])
        child_base_categories = self.env['product.category'].search([('id', 'child_of', base_category.id)])
        base_ingredients = products.filtered(lambda rec: rec.categ_id.id in (base_category | child_base_categories).ids)
        active_ingredients = products.filtered(
            lambda rec: rec.categ_id.id in (active_category | child_active_categories).ids)
        quality_wo = self.workorder_ids.filtered(lambda wo: wo.workcenter_id.quality_station)
        production_wo = self.workorder_ids.filtered(lambda wo: wo.workcenter_id.production_station)
        packaging_wo = self.workorder_ids.filtered(lambda wo: wo.workcenter_id.packaging_station)[:1]
        packaging_images = []
        packaging_images_count = max([
            len(packaging_wo.current_packaging_image_line_ids),
            len(packaging_wo.current_packaging_image_line_ids),
        ])
        for number in range(packaging_images_count):
            previous_image, current_image = False, False
            if number < len(packaging_wo.current_packaging_image_line_ids):
                current_image = packaging_wo.current_packaging_image_line_ids[number].image
            if number < len(packaging_wo.previous_packaging_image_lines_ids):
                previous_image = packaging_wo.previous_packaging_image_lines_ids[number].image
            packaging_images.append({'current_image': current_image, 'previous_image': previous_image})

        packaging_worksheet_checks = packaging_wo.check_ids.filtered(lambda ch: ch.test_type == 'worksheet')
        packaging_worksheet_images = {}
        for packaging_worksheet_check in packaging_worksheet_checks:
            packaging_check_template = packaging_worksheet_check.worksheet_template_id.model_id.model
            packaging_worksheet = self.env[packaging_check_template].search([
                ('x_quality_check_id', '=', packaging_worksheet_check.id),
            ])
            worksheet_fields = packaging_worksheet.fields_get()
            packaging_binary_fields = {i: y.get('string') for i, y in worksheet_fields.items() if
                                       y.get('type') == 'binary'}
            packaging_worksheet_images.update(
                {y: packaging_worksheet.__getattribute__(i) for i, y in packaging_binary_fields.items()})

        packaging_worksheet_images = [
            list(packaging_worksheet_images.items())[i:i + 2]
            for i in range(0, len(packaging_worksheet_images), 2)
        ]

        analyses_data = {}
        if quality_wo:
            analyses_data = {}
            check_template = quality_wo.check_ids.worksheet_template_id.model_id.model
            check_id = quality_wo.check_ids.id
            quality_worksheet = self.env[check_template].search([('x_quality_check_id', '=', check_id)])
            check_status = quality_wo.check_ids.quality_state
            if quality_worksheet:
                worksheet_fields = quality_worksheet.fields_get()
                binary_fields = {i: y.get('string') for i, y in worksheet_fields.items() if y.get('type') == 'binary'}
                worksheet_images = {y: quality_worksheet.__getattribute__(i) for i, y in binary_fields.items()}

                worksheet_images = [
                    list(worksheet_images.items())[i:i + 2]
                    for i in range(0, len(worksheet_images), 2)
                ]
                quality_check.append({'name': 'Appearence', 'value': 'Chew', 'method': 'Visual'})
                if worksheet_fields.get('x_studio_color'):
                    quality_check.append(
                        {'name': 'Color', 'value': quality_worksheet.x_studio_color, 'method': 'Visual'})
                if worksheet_fields.get('x_previous_color'):
                    quality_check.append(
                        {'name': 'Previos Color', 'value': quality_worksheet.x_previous_color, 'method': 'Visual'})
                if worksheet_fields.get('x_previous_lot_id'):
                    analyses_data.update({'previous_lot_id': quality_worksheet.x_previous_lot_id.name})
                if worksheet_fields.get('x_studio_weight_of_chew'):
                    quality_check.append(
                        {'name': 'Weight Of Chew', 'value': quality_worksheet.x_studio_weight_of_chew,
                         'method': 'Device'})
                if worksheet_fields.get('x_studio_add_measure_result'):
                    quality_check.append(
                        {'name': 'Measure Result', 'value': quality_worksheet.x_studio_add_measure_result,
                         'method': 'Device'})
        analyses_data.update({
            'base_ingredients': base_ingredients,
            'active_ingredients': active_ingredients,
            'quality_wo': quality_wo,
            'production_wo': production_wo,
            'quality_check': quality_check,
            'check_status': check_status,
            'worksheet_images': worksheet_images,
            'workorders_operators': workorders_operators,
            'packaging_images': packaging_images,
            'packaging_worksheet_images': packaging_worksheet_images,
        })
        return analyses_data

    def _get_check_worksheet_images(self, check):
        if check.test_type != 'worksheet':
            return {}
        worksheet = self.env[check.worksheet_template_id.model_id.model].search([('x_quality_check_id', '=', check.id)])
        worksheet_fields = worksheet.fields_get()
        binary_fields = {i: y.get('string') for i, y in worksheet_fields.items() if y.get('type') == 'binary'}
        worksheet_images = {y: worksheet.__getattribute__(i) for i, y in binary_fields.items()}
        return worksheet_images




    def _get_bom_structure_data(self):
        total_base, total_active, total_packaging = 0, 0, 0
        bom_lines = self.bom_id.bom_line_ids
        premix_wo = self.workorder_ids.filtered(lambda rec: rec.workcenter_id.premix_station)
        packaging_wo = self.workorder_ids.filtered(lambda rec: rec.workcenter_id.packaging_station)
        base_lines = []
        active_lines = []
        packaging_lines = []
        active_category = self.env['product.category'].search([('name', 'ilike', 'Active Ingredients')], limit=1)
        base_category = self.env['product.category'].search([('name', 'ilike', 'Base Ingredients')], limit=1)
        child_active_categories = self.env['product.category'].search([('id', 'child_of', active_category.id)])
        child_base_categories = self.env['product.category'].search([('id', 'child_of', base_category.id)])
        if premix_wo or packaging_wo:
            for line in bom_lines:
                if line.operation_id.workcenter_id.premix_station:
                    check_ids = premix_wo.check_ids
                    if line.product_id.categ_id.id in child_base_categories.ids:
                        total_base += line.product_qty
                        lot = check_ids.filtered(lambda check: check.component_id == line.product_id)[:1]
                        base_lines.append({'bom_line': line, 'lot': lot.lot_id if lot else None})
                    elif line.product_id.categ_id.id in child_active_categories.ids:
                        total_active += line.product_qty
                        lot = check_ids.filtered(lambda check: check.component_id == line.product_id)[:1]
                        active_lines.append({'bom_line': line, 'lot': lot.lot_id if lot else None})
                else:
                    check_ids = packaging_wo.check_ids
                    if line.product_id.tracking == 'lot':
                        total_packaging += line.product_qty
                        lot = check_ids.filtered(lambda check: check.component_id == line.product_id)[:1]
                        packaging_lines.append({'bom_line': line, 'lot': lot.lot_id if lot else None})

        bom_structure = {
            'total_base': total_base,
            'total_active': total_active,
            'total_packaging': total_packaging,
            'total_weight': total_base + total_active,
            'base_lines': base_lines,
            'active_lines': active_lines,
            'packaging_lines': packaging_lines,
            'batches_count': self.batches_count
        }
        return bom_structure

    def _get_batch_record_data(self):
        batch_records = batch_data = {}
        production_wo = self.workorder_ids.filtered(lambda wo: wo.workcenter_id.production_station)
        if production_wo:
            cutting_time = production_wo.workcenter_id.cutting_time * self.batches_count
            for batch_check in production_wo.workorder_batch_checks_ids:
                title = batch_check.title if 'mixing' not in batch_check.title.lower() else 'Mixing'
                value = batch_check.time_actual
                if title in batch_records:
                    batch_records[title] += value
                else:
                    batch_records[title] = value
            batch_data = {
                'batch_records': [{'title': title, 'value': batch_records[title]} for title in batch_records],
                'cutting_time': cutting_time,
            }
        return batch_data

    def get_time_with_timezone(self, workorder, time):
        resource_calendar = workorder.workcenter_id.resource_calendar_id or self.env.company.resource_calendar_id
        calendar_tz = pytz.timezone(resource_calendar.tz)
        time_with_timezone = time.astimezone(calendar_tz).replace(tzinfo=None)
        return time_with_timezone

    def action_view_production_cleaning(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Production Cleaning',
            'res_model': 'mrp.production',
            'views': [[self.env.ref('mrp.mrp_production_form_view').id, 'form']],
            'res_id': self.production_cleaning_order_id.id,
            'target': 'main',
        }

    def action_view_packaging_cleaning(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Packaging Cleaning',
            'res_model': 'mrp.production',
            'views': [[self.env.ref('mrp.mrp_production_form_view').id, 'form']],
            'res_id': self.packaging_cleaning_order_id.id,
            'target': 'main',
        }

    def button_mark_done(self):
        self = self.sudo()
        res = super(MrpProduction, self).button_mark_done()
        picking_type_id = self.env['ir.config_parameter'].sudo().get_param('aznut_mrp.picking_type_id')
        location_id = self.env['ir.config_parameter'].sudo().get_param('aznut_mrp.location_id')
        location_dest_id = self.env['ir.config_parameter'].sudo().get_param('aznut_mrp.location_dest_id')
        for rec in self:
            is_cleaning = any(
                wo.workcenter_id.production_area_cleaning_station or
                wo.workcenter_id.packaging_area_cleaning_station
                for wo in rec.workorder_ids)
            if is_cleaning and not rec.product_qty:
                rec.product_qty = 1.00
        if picking_type_id and location_id and location_dest_id:
            for order in self.filtered(lambda rec: not rec.store_picking_id):
                picking_vals = {
                    'picking_type_id': int(picking_type_id),
                    'location_id': int(location_id),
                    'location_dest_id': int(location_dest_id),
                    'origin': order.display_name,
                    'active': False,
                    'move_lines': [(0, 0, {
                        'product_id': order.product_id.id,
                        'product_uom': order.product_uom_id.id,
                        'product_uom_qty': order.qty_produced,
                        'name': order.product_id.partner_ref,
                        'location_id': int(location_id),
                        'location_dest_id': int(location_dest_id),
                    })]
                }
                picking = self.env['stock.picking'].create(picking_vals)
                if order.workorder_ids:
                    is_cleaning = any(
                        wo.workcenter_id.production_area_cleaning_station or
                        wo.workcenter_id.packaging_area_cleaning_station
                        for wo in order.workorder_ids)
                    if is_cleaning:
                        picking.action_cancel()
                order.store_picking_id = picking

        self.update_product_standard_cost()
        self.assign_transfers()
        self.filtered(lambda mo: mo.state == 'done')._confirm_quantity_moves()
        return res

    def update_product_standard_cost(self):
        for order in self.filtered(lambda mo: mo.state == 'done'):
            currency_table = self.env['res.currency']._get_query_currency_table(
                {'multi_company': True, 'date': {'date_to': fields.Date.today()}})
            total_cost, operation_cost = 0, 0
            query_str = """
            SELECT
                abs(SUM(svl.value)),
                currency_table.rate
                FROM stock_move AS sm
            INNER JOIN stock_valuation_layer AS svl ON svl.stock_move_id = sm.id
            LEFT JOIN mrp_production AS mo on sm.raw_material_production_id = mo.id
            LEFT JOIN {currency_table} ON currency_table.company_id = mo.company_id
                WHERE sm.raw_material_production_id in %s AND sm.state != 'cancel' AND sm.product_qty != 0 AND scrapped != 't'
            GROUP BY sm.product_id, mo.id, currency_table.rate""".format(currency_table=currency_table, )
            self.env.cr.execute(query_str, ((order.id,),))
            for cost, currency_rate in self.env.cr.fetchall():
                cost *= currency_rate
                total_cost += cost

            workorders = order.workorder_ids
            if workorders:
                query_str = """SELECT
                                    (
                                        SELECT COALESCE(CASE
                                            WHEN wc.production_station IS NOT NULL THEN SUM(
                                                CASE
                                                    WHEN unique_mwb.time_finish IS NULL THEN EXTRACT(EPOCH FROM AGE(CURRENT_DATE, unique_mwb.time_start))
                                                    ELSE EXTRACT(EPOCH FROM (unique_mwb.time_finish - unique_mwb.time_start)) / 60 
                                                END
                                            )
                                            ELSE SUM(t.duration)
                                        END, 0)
                                        FROM mrp_workorder_batch AS unique_mwb
                                        WHERE unique_mwb.workorder_id = wo.id
                                    ) AS total_duration,
                                    CASE WHEN wo.costs_hour = 0.0 THEN wc.costs_hour ELSE wo.costs_hour END AS costs_hour,
                                    currency_table.rate
                                FROM mrp_workcenter_productivity t
                                LEFT JOIN mrp_workorder wo ON (wo.id = t.workorder_id)
                                LEFT JOIN mrp_workorder_batch mwb ON mwb.workorder_id = wo.id
                                LEFT JOIN mrp_workcenter wc ON (wc.id = t.workcenter_id)
                                LEFT JOIN res_users u ON (t.user_id = u.id)
                                LEFT JOIN res_partner partner ON (u.partner_id = partner.id)
                                LEFT JOIN mrp_routing_workcenter op ON (wo.operation_id = op.id)
                                LEFT JOIN {currency_table} ON currency_table.company_id = t.company_id
                                WHERE t.workorder_id IS NOT NULL AND t.workorder_id IN %s
                                GROUP BY wo.production_id, wo.id, op.id, wo.name, wc.costs_hour, wc.production_station, partner.name, t.user_id, currency_table.rate
                                ORDER BY wo.name, partner.name
                                        """.format(currency_table=currency_table, )
                self.env.cr.execute(query_str, (tuple(workorders.ids),))
                for duration, cost_hour, currency_rate in self.env.cr.fetchall():
                    operation_cost += (duration / 60.0) * (cost_hour * currency_rate)

            cost = (total_cost + operation_cost) / (self.product_uom_qty or 1)
            sale_lines = order.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id.order_line
            suitable_line = sale_lines.filtered(lambda line: line.product_id == order.product_id)[:1]
            if suitable_line:
                suitable_line = suitable_line.with_company(suitable_line.company_id)
                suitable_line.write({
                    'production_purchase_price': suitable_line._convert_price(cost,
                                                                              suitable_line.product_id.uom_id),
                })
                suitable_line.order_id.write({'show_production_margin': True})

    def assign_transfers(self):
        for order in self.filtered(lambda mo: mo.picking_ids):
            order.picking_ids.action_assign()

    def action_view_store_pickings(self):
        self.ensure_one()
        if not self.store_picking_id.active:
            self.store_picking_id.write({'active': True})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Store Picking',
            'res_model': 'stock.picking',
            'views': [[self.env.ref('stock.view_picking_form').id, 'form']],
            'res_id': self.store_picking_id.id,
            'target': 'main',
        }

    def action_set_scheduled_date(self):
        return {
            'name': 'Set Scheduled Date',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'set.scheduled.date.wizard',
            'view_id': self.env.ref('aznut_mrp.set_scheduled_date_wizard_form').id,
            'target': 'new',
            'context': {'default_production_orders_ids': self.ids}
        }



    def is_production_started(self):
        wo_states = ['done', 'progress']
        progress_wo = self.workorder_ids.filtered(lambda wo: wo.state in wo_states)
        return bool(progress_wo)

    def _get_ready_to_produce_state(self):
        self.ensure_one()
        operations = self.workorder_ids.operation_id
        if len(operations) == 1:
            moves_in_first_operation = self.move_raw_ids
        else:
            first_operation = operations[0]
            moves_in_first_operation = self.move_raw_ids.filtered(lambda move: move.operation_id == first_operation)
        if self._context.get('from_mrp'):
            moves_in_first_operation = moves_in_first_operation.filtered(
                lambda move: not move.product_id.categ_id.is_removed_from_availability)
        moves_in_first_operation = moves_in_first_operation.filtered(
            lambda move: move.bom_line_id and
                         not move.bom_line_id._skip_bom_line(self.product_id)
        )

        if all(move.state == 'assigned' for move in moves_in_first_operation):
            return 'assigned'
        return 'confirmed'

    def create_backorder(self):
        for record in self:
            if 0 < record.qty_producing < record.product_qty:
                record._generate_backorder_productions(close_mo=False)
                record.product_qty = record.qty_producing


    def write(self, vals):
        res = super(MrpProduction, self).write(vals)
        if self.state in ['confirmed', 'progress']:
            self._update_production_batches()
            self._update_premix_checks()
            self.move_raw_ids._update_manufacturing_checks()
        if vals.get('aznut_priority'):
            self._change_priority()
        return res

    @api.model
    def create(self, values):
        res = super(MrpProduction, self).create(values)
        if values.get('aznut_priority'):
            res._change_priority()
        return res

    def _change_priority(self):
        for rec in self.filtered(lambda rec: rec.state in ['confirmed']):
            date_planned_start = rec.date_planned_start
            start_of_day = datetime.combine(date_planned_start.date(), datetime.min.time())
            end_of_day = datetime.combine(date_planned_start.date(), datetime.max.time())
            this_date_mos = self.env['mrp.production'].sudo().search([
                ('state', 'in', ['confirmed']),
                ('date_planned_start', '<=', end_of_day),
                ('date_planned_start', '>=', start_of_day),
            ]) | rec
            this_date_mos.button_unplan()
            this_date_mos.update({'date_planned_start': start_of_day})
            this_date_mos.sorted(
                key=lambda rec: int(rec.aznut_priority), reverse=True
            ).button_plan()

    def _confirm_quantity_moves(self):
        for rec in self.filtered(lambda mo: mo.is_quantity_confirmed):
            sfp = rec.picking_ids.filtered(
                lambda pick: pick.picking_type_code == 'internal' and pick.state not in ['done', 'cancel'])[:1]
            moves = sfp.move_lines.filtered(lambda mv: mv.product_id.id == rec.product_id.id)
            if not moves:
                continue
            needed_move = max(moves, key=lambda move: move.product_uom_qty)
            if needed_move:
                sfp.do_unreserve()
                moves_to_delete = moves - needed_move
                if moves_to_delete:
                    moves_to_delete.write({
                        'state': 'draft',
                    })
                    moves_to_delete.unlink()
                needed_move.write({
                    'product_uom_qty': rec.qty_producing,
                    'move_orig_ids': rec.move_finished_ids.ids,
                })
                sfp.action_assign()

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        res = super(MrpProduction, self).search(args, offset=offset, limit=limit, order=order, count=count)
        if self._context.get('color_sorting') and not isinstance(res, int):
            if ['reservation_state', '=', 'assigned'] in args and ['state', '=', 'confirmed'] in args:
                return res.sorted(lambda rec: (rec.product_id.mrp_color is False, int(rec.product_id.mrp_color) if str(
                    rec.product_id.mrp_color).isdigit() else float('inf')))
        return res
