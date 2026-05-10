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

from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError

from odoo.tools import float_compare, float_is_zero

from math import ceil

from datetime import timedelta, timezone, datetime
import pytz


def get_minutes(time_start, time_finish):
    if time_start and time_finish:
        diff = time_finish - time_start
        return diff.total_seconds() / 60
    return 0


def check_is_suitable_for_productivity(batch):
    return batch.time_start and batch.time_finish and batch.workorder_id.workcenter_id


categories_to_exclude = ['Dog Treats Packaging materials', 'Jar Labels']


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    @api.constrains('employees_ids')
    def _check_employees_ids(self):
        for workorder in self:
            else_workorders = workorder.production_id.workorder_ids - workorder
            fail_message_list = []
            for employee in workorder.employees_ids:
                fail_workorders = else_workorders.filtered(lambda wo: employee.id in wo.employees_ids.ids)
                if fail_workorders:
                    wo_names = ', '.join(fail_workorders.mapped('name'))
                    fail_message = 'Employee %s is already assigned to: %s.' % (employee.display_name, wo_names)
                    fail_message_list.append(fail_message)
            if fail_message_list:
                raise ValidationError('\n'.join(fail_message_list))

    product_lots_ids = fields.Many2many(
        'stock.production.lot',
        compute='_compute_product_lots_ids',
    )
    production_station = fields.Boolean(
        string='Production Station',
        related='workcenter_id.production_station',
    )
    premix_station = fields.Boolean(
        string='Premix Station',
        related='workcenter_id.premix_station',
    )
    packaging_station = fields.Boolean(
        string='Premix Station',
        related='workcenter_id.packaging_station',
    )
    hide_mark_as_done_button = fields.Boolean(
        related='workcenter_id.hide_mark_as_done_button',
        string='Hide Mark As Done Button',
    )
    production_status = fields.Selection(
        [('none', 'None'), ('draft', 'Draft'), ('in_progress', 'In Progress'), ('done', 'Done')],
        string='Production Status',
        default='none',
        copy=False
    )
    hide_mark_as_done_and_close_button = fields.Boolean(
        related='workcenter_id.hide_mark_as_done_and_close_button',
        string='Hide Mark as Done and Close',
    )
    current_quality_check_premix_line_ids = fields.One2many(
        'quality.check.premix.line',
        related='current_quality_check_id.quality_check_premix_line_ids',
        string='Current Quality Check Premix Lines'
    )
    has_quality_check_premix_lines = fields.Boolean(
        string='Has Quality Check Premix Lines',
        compute='_compute_has_quality_check_premix_lines',
    )
    show_validate_button = fields.Boolean(
        compute='_compute_show_validate_button',
        string='Show Validate Button',
    )
    workorder_batch_ids = fields.One2many(
        'mrp.workorder.batch',
        'workorder_id',
        string='Batches',
    )
    current_workorder_batch_id = fields.Many2one(
        'mrp.workorder.batch',
        string='Current Batch',
    )
    current_workorder_batch_name = fields.Char(
        string='Current Batch Name',
        related='current_workorder_batch_id.name'
    )
    current_workorder_batch_quantity = fields.Float(
        string='Current Batch Quantity',
        related='current_workorder_batch_id.quantity',
    )
    current_workorder_batch_is_validated = fields.Boolean(
        string='Current Batch Validated',
        related='current_workorder_batch_id.is_validated',
        readonly=False,
    )
    next_workorder_batch_id = fields.Many2one(
        'mrp.workorder.batch',
        string='Next Batch',
        compute='_compute_next_and_previous_workorder_batch_id'
    )
    previous_workorder_batch_id = fields.Many2one(
        'mrp.workorder.batch',
        string='Previous Batch',
        compute='_compute_next_and_previous_workorder_batch_id'
    )
    batches_produced_quantity = fields.Float(
        string='Produced',
        readonly=True,
        copy=False,
    )
    show_finish_batches_button = fields.Boolean(
        string='Show Finish Batches Button',
        compute='_compute_show_finish_batches_button',
    )
    next_production_check_id = fields.Many2one(
        'quality.check',
        string='Next Production Check',
        compute='_compute_next_and_previous_production_check_id'
    )
    previous_production_check_id = fields.Many2one(
        'quality.check',
        string='Previous Production Check',
        compute='_compute_next_and_previous_production_check_id'
    )
    current_production_check_lines_ids = fields.Many2many(
        'quality.check.production.line',
        string='Current Quality Check Production Lines',
        readonly=True,
    )
    current_production_check_id = fields.Many2one(
        'quality.check',
        string='Current Production Check'
    )
    production_checks_ids = fields.Many2many(
        'quality.check',
        string='Production Quality Checks',
        copy=False,
    )
    current_production_check_state = fields.Selection(
        related='current_production_check_id.quality_state',
        string='Current Quality Check State',
    )
    current_production_check_note = fields.Html(
        related='current_production_check_id.note',
        string='Current Production Check Note',
    )
    current_production_check_not_create_components = fields.Boolean(
        related='current_production_check_id.not_create_components',
        string='Current Production Check Not Create Components',
    )
    highlight_next_check_button = fields.Boolean(
        string='Highlight Next Check Button',
        compute='_compute_highlight_next_check_button',
    )
    show_current_production_check_lines_ids = fields.Boolean(
        compute='_compute_show_current_quality_check_production_lines_ids',
        string='Show Current Quality Checks Production Lines',
    )
    show_calculate_batches_produced_quantity_button = fields.Boolean(
        compute='_compute_show_calculate_batches_produced_quantity_button',
        string='Show Calculate Batches Button',
    )
    has_production_batches = fields.Boolean(
        string='Has Production Batches',
        compute='_compute_has_production_batches',
    )
    has_production_batch_checks = fields.Boolean(
        string='Has Production Batch Checks',
        compute='_compute_has_production_batch_checks',
    )
    current_workorder_batch_check_id = fields.Many2one(
        'mrp.workorder.batch.check',
        string='Current Workorder Batch Check',
        compute='_compute_current_workorder_batch_check_id',
    )
    workorder_batch_checks_ids = fields.Many2many(
        'mrp.workorder.batch.check',
        string="Work Order Batch Checks",
        readonly=True,
    )
    first_production_check_id = fields.Many2one(
        'quality.check',
        string='First Production Check',
        compute='_compute_first_production_check_id',
    )
    show_return_to_the_first_check_button = fields.Boolean(
        string='Show Return To The First Check Button',
        compute='_compute_show_return_to_the_first_check_button',
    )
    done_user = fields.Many2one(
        'res.users',
        string='User who done workorder'
    )
    show_additional_lots = fields.Boolean(
        string='Show Additional Lots',
        compute='_compute_show_additional_lots',
    )
    show_lots_in_checks = fields.Boolean(
        string='Show Lots In Checks',
        compute='_compute_show_lots_in_checks',
    )
    package_lines_ids = fields.Many2many(
        'package.line',
        string='Package Lines',
        readonly=True,
        copy=False,
    )
    show_number_packages_wizard = fields.Boolean(
        string='Show Number Packages Wizard',
        compute='_compute_show_number_packages_wizard'
    )
    show_package_lines = fields.Boolean(
        string='Show Package Lines',
        compute='_compute_show_package_lines',
    )
    show_print_containers_labels_button = fields.Boolean(
        compute='_compute_show_print_containers_labels_button',
    )
    employees_ids = fields.Many2many(
        'hr.employee',
        string='Operators',
        copy=False,
    )
    done_employees_ids = fields.Many2many(
        'hr.employee',
        'done_employees_rel',
        'done_employee_id',
        string='Done Operators',
        copy=False,
    )
    show_confirm_production_quantity_button = fields.Boolean(
        string='Show Confirm Production Quantity Button',
        compute='_compute_show_confirm_production_quantity_button',
    )
    workorder_scrap_line_ids = fields.One2many(
        'workorder.scrap.line',
        'workorder_id',
        string='Work Order Scrap Lines',
    )
    current_packaging_image_line_ids = fields.One2many(
        'packaging.image.line',
        'workorder_id',
        string='Current Packaging Images',
    )
    previous_packaging_image_lines_ids = fields.Many2many(
        'packaging.image.line',
        compute='_compute_previous_packaging_image_lines_ids',
    )
    packaging_activity_line_ids = fields.One2many(
        'packaging.activity.line',
        'workorder_id',
        string='Packaging Activity Lines',
    )
    workorder_note = fields.Text(
        string='WorkOrder Note',
    )
    production_workorder_ids = fields.Many2many(
        'mrp.workorder',
        string='Production WorkOrders',
        compute='_compute_production_workorder_ids',
    )
    is_lot_validated = fields.Boolean(
        related='production_id.is_lot_validated',
    )
    is_duration_expired = fields.Boolean(
        string='Is Duration Expired',
        compute='_compute_is_duration_expired',
    )
    mrp_color = fields.Selection(
        related='production_id.mrp_color',
    )
    block_reasons_ids = fields.Many2many(
        'mrp.workcenter.productivity',
        string='Block Reasons',
        compute='_compute_block_reasons_ids'
    )
    night_shift_user = fields.Boolean(
        string='Night Shift User',
        compute='_compute_night_shift_user',
    )
    has_pump_uom = fields.Boolean(
        string='Has Pump UOM',
        compute='_compute_has_pump_uom',
    )

    @api.depends('current_quality_check_premix_line_ids')
    def _compute_has_pump_uom(self):
        self.has_pump_uom = False
        for wo in self:
            if wo.current_quality_check_premix_line_ids.filtered(
                    lambda line: line.pump_uom) or wo.current_production_check_lines_ids.filtered(
                    lambda line: line.pump_uom):
                wo.has_pump_uom = True

    def _compute_block_reasons_ids(self):
        for wo in self:
            domain = [
                ('block_workorder_id', '=', wo.id),
            ]
            wo.block_reasons_ids = self.env['mrp.workcenter.productivity'].search(domain)

    def _compute_night_shift_user(self):
        self.night_shift_user = self.env.user.night_shift_user

    def _compute_show_number_packages_wizard(self):
        self.show_number_packages_wizard = False
        for wo in self:
            packaging_wo = wo.production_id.workorder_ids.filtered(
                lambda wo: wo.workcenter_id.packaging_station and wo.state != 'done')[:1]
            if wo.workcenter_id.quality_station and not packaging_wo.package_lines_ids:
                wo.show_number_packages_wizard = True

    def _compute_is_duration_expired(self):
        expired = self.filtered(lambda wo: wo.duration > wo.duration_expected)
        expired.is_duration_expired = True
        (self - expired).is_duration_expired = False

    def _compute_production_workorder_ids(self):
        for wo in self:
            wo.production_workorder_ids = wo.production_id.workorder_ids

    def _compute_previous_packaging_image_lines_ids(self):
        for wo in self:
            previous_wo = self.env['mrp.workorder'].search([
                ('product_id', '=', wo.product_id.id),
                ('current_packaging_image_line_ids', '!=', False),
                ('id', '!=', wo.id),
            ], order='create_date DESC', limit=1)
            wo.previous_packaging_image_lines_ids = previous_wo.current_packaging_image_line_ids

    def _compute_show_print_containers_labels_button(self):
        self.show_print_containers_labels_button = False
        for wo in self.filtered(lambda rec: rec.is_last_step and rec.premix_station and rec.is_user_working):
            wo.show_print_containers_labels_button = True

    def _compute_show_lots_in_checks(self):
        self.show_lots_in_checks = False
        for workorder in self:
            if workorder.current_quality_check_id.quality_check_premix_line_ids.reserved_lots_ids:
                workorder.show_lots_in_checks = True

    def _compute_show_additional_lots(self):
        self.show_additional_lots = False
        for workorder in self:
            if workorder.product_lots_ids:
                workorder.show_additional_lots = True

    def _compute_product_lots_ids(self):
        for workorder in self:
            workorder.product_lots_ids = workorder.mapped(
                'current_quality_check_id.move_id.move_line_ids.lot_id').filtered(
                lambda lot: lot != workorder.lot_id
            )

    @api.depends('current_production_check_id', 'production_checks_ids')
    def _compute_show_return_to_the_first_check_button(self):
        self.show_return_to_the_first_check_button = False
        for workorder in self:
            first_check, current_check = workorder.first_production_check_id, workorder.current_production_check_id
            if first_check and first_check != current_check:
                workorder.show_return_to_the_first_check_button = True

    @api.depends('production_checks_ids')
    def _compute_first_production_check_id(self):
        for workorder in self:
            workorder.first_production_check_id = workorder.production_checks_ids[:1]

    @api.depends('workcenter_id.premix_station', 'current_quality_check_premix_line_ids.is_checked')
    def _compute_show_validate_button(self):
        self.show_validate_button = True
        for workorder in self:
            if workorder.workcenter_id.premix_station:
                if workorder.current_quality_check_premix_line_ids.filtered(lambda line: not line.is_checked):
                    workorder.show_validate_button = False

    @api.depends('current_quality_check_id')
    def _compute_has_quality_check_premix_lines(self):
        for workorder in self:
            workorder.has_quality_check_premix_lines = bool(workorder.current_quality_check_premix_line_ids)

    @api.depends('check_ids.quality_state')
    def _compute_show_finish_batches_button(self):
        self.show_finish_batches_button = True
        for rec in self:
            if rec.check_ids.filtered(lambda check: check.quality_state == 'none'):
                rec.show_finish_batches_button = False

    @api.depends('current_workorder_batch_id')
    def _compute_next_and_previous_workorder_batch_id(self):
        self.next_workorder_batch_id, self.previous_workorder_batch_id = False, False
        for workorder in self:
            sorted_workorder_batch_ids = workorder.workorder_batch_ids.sorted('id').ids
            if workorder.current_workorder_batch_id.id in sorted_workorder_batch_ids:
                current_position = sorted_workorder_batch_ids.index(workorder.current_workorder_batch_id.id)
                if current_position + 2 <= len(sorted_workorder_batch_ids):
                    next_workorder_batch_id = sorted_workorder_batch_ids[current_position + 1]
                    workorder.next_workorder_batch_id = self.env['mrp.workorder.batch'].browse(
                        next_workorder_batch_id
                    )
                if current_position - 1 >= 0:
                    previous_workorder_batch_id = sorted_workorder_batch_ids[current_position - 1]
                    workorder.previous_workorder_batch_id = self.env['mrp.workorder.batch'].browse(
                        previous_workorder_batch_id
                    )

    @api.depends('current_workorder_batch_id')
    def _compute_next_and_previous_production_check_id(self):
        self.previous_production_check_id, self.next_production_check_id = False, False
        for workorder in self:
            sorted_production_checks_ids = workorder.production_checks_ids.sorted('id').ids
            if workorder.current_production_check_id.id in sorted_production_checks_ids:
                current_position = sorted_production_checks_ids.index(workorder.current_production_check_id.id)
                if current_position + 2 <= len(sorted_production_checks_ids):
                    next_production_check_id = sorted_production_checks_ids[current_position + 1]
                    workorder.next_production_check_id = self.env['quality.check'].browse(
                        next_production_check_id
                    )
                if current_position - 1 >= 0:
                    previous_production_check_id = sorted_production_checks_ids[current_position - 1]
                    workorder.previous_production_check_id = self.env['quality.check'].browse(
                        previous_production_check_id
                    )

    def _compute_show_current_quality_check_production_lines_ids(self):
        self.show_current_production_check_lines_ids = False
        for rec in self:
            if rec.current_production_check_lines_ids:
                rec.show_current_production_check_lines_ids = True

    @api.depends('current_production_check_lines_ids.is_checked')
    def _compute_highlight_next_check_button(self):
        self.highlight_next_check_button = False
        for rec in self:
            if not rec.current_production_check_lines_ids.filtered(lambda line: not line.is_checked):
                rec.highlight_next_check_button = True

    @api.depends('production_checks_ids.quality_state', 'current_workorder_batch_is_validated')
    def _compute_show_calculate_batches_produced_quantity_button(self):
        self.show_calculate_batches_produced_quantity_button = False
        for rec in self:
            if not rec.current_workorder_batch_is_validated:
                fail_checks = rec.production_checks_ids.filtered(lambda check: check.quality_state == 'fail')
                if not fail_checks and not self.next_production_check_id:
                    rec.show_calculate_batches_produced_quantity_button = True

    @api.depends('check_ids')
    def _compute_finished_product_check_ids(self):
        for wo in self:
            checks = wo.check_ids | wo.production_checks_ids
            wo.finished_product_check_ids = checks.filtered(lambda c: c.finished_product_sequence == wo.qty_produced)

    @api.depends('workorder_batch_ids')
    def _compute_has_production_batches(self):
        self.has_production_batches = False
        for wo in self:
            if wo.workorder_batch_ids:
                wo.has_production_batches = True

    @api.depends('workorder_batch_checks_ids')
    def _compute_has_production_batch_checks(self):
        self.has_production_batch_checks = False
        for wo in self:
            if wo.workorder_batch_checks_ids:
                wo.has_production_batch_checks = True

    @api.depends('current_workorder_batch_id', 'current_production_check_id')
    def _compute_current_workorder_batch_check_id(self):
        for wo in self:
            check = self.env['mrp.workorder.batch.check'].search([
                ('production_check_id', '=', wo.current_production_check_id.id),
                ('workorder_batch_id', '=', wo.current_workorder_batch_id.id)
            ], limit=1)
            wo.current_workorder_batch_check_id = check

    def _compute_show_confirm_production_quantity_button(self):
        self.show_confirm_production_quantity_button = False
        for wo in self:
            not_done_checks = wo.check_ids.filtered(lambda check: check.quality_state == 'none')
            if wo.is_last_unfinished_wo and wo.packaging_station and not wo.production_id.is_quantity_confirmed and not wo.skipped_check_ids and wo.is_last_step:
                wo.show_confirm_production_quantity_button = True

    def _compute_working_users(self):
        for order in self.sudo():
            order.working_user_ids = [(4, order.id) for order in order.time_ids.filtered(lambda time: not time.date_end).sorted('date_start').mapped('user_id')]
            if order.working_user_ids:
                order.last_working_user_id = order.working_user_ids[-1]
            elif order.time_ids:
                order.last_working_user_id = order.time_ids.filtered('date_end').sorted('date_end')[-1].user_id if order.time_ids.filtered('date_end') else order.time_ids[-1].user_id
            else:
                order.last_working_user_id = False
            if order.time_ids.filtered(lambda x: (x.user_id.id == self.env.user.id) and (not x.date_end) and (x.loss_type in ('productive', 'performance'))):
                order.is_user_working = True
            else:
                order.is_user_working = False

    def _get_report_containers_labels_data(self):
        self.ensure_one()
        containers_lines_dict = {}
        premix_lines = self.check_ids.quality_check_premix_line_ids
        for premix_line in premix_lines.filtered(lambda line: line.container_number):
            if not containers_lines_dict.get(premix_line.container_number, False):
                containers_lines_dict[premix_line.container_number] = self.env['quality.check.premix.line']
            containers_lines_dict[premix_line.container_number] |= premix_line
        return {k: v for k, v in sorted(containers_lines_dict.items())}

    def _get_total_weight(self, container):
        self.ensure_one()
        lines = self._get_report_containers_labels_data().get(container)
        return sum(map(lambda line: line._get_weight(), lines))

    def action_print_containers_labels(self):
        wos_ids = self.filtered(lambda wo: wo.premix_station).ids
        return self.env.ref('aznut_mrp.action_report_containers_labels').report_action(wos_ids)

    def validate_package_lines(self, response):
        self.ensure_one()
        barcode = response['barcode']
        lines = self.package_lines_ids.filtered(lambda ln: not ln.is_validated)
        if not self.finished_lot_id.name or not lines:
            raise ValidationError(_('No need to scan barcode!'))
        elif barcode != self.finished_lot_id.name:
            raise ValidationError(_('Invalid Barcode!'))
        lines[:1].action_validate()

    def open_tablet_view(self):
        self.ensure_one()
        res = super(MrpWorkorder, self).open_tablet_view()
        for check in self.check_ids:
            if check.test_type not in ('register_consumed_materials', 'register_byproducts'):
                continue
            check.write(self._defaults_from_move(check.move_id))
        res['context'].update({
            'aznut_mrp': True,
            'workorder_id': self.id,
        })
        return res

    def action_batches_menu(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'views': [[self.env.ref('aznut_mrp.mrp_workorder_view_form_tablet_menu_inherit').id, 'form']],
            'name': _('Menu'),
            'target': 'new',
            'res_id': self.id,
        }

    def action_open_number_packages_wizard(self):
        self.ensure_one()
        return {
            'name': _('Set Number Of Packages'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'number.packages.wizard',
            'view_id': self.env.ref('aznut_mrp.number_packages_wizard_form').id,
            'target': 'new',
            'context': {'default_production_id': self.production_id.id}
        }

    def _compute_show_package_lines(self):
        self.show_package_lines = False
        for wo in self:
            if wo.package_lines_ids:
                wo.show_package_lines = True

    @api.depends('production_availability',
                 'production_id.move_raw_ids.product_id.categ_id.is_removed_from_premix_availability')
    def _compute_state(self):
        for workorder in self:
            if workorder.state not in ('waiting', 'ready'):
                continue
            if not workorder.premix_station:
                reservation_state = workorder.production_id.reservation_state
            else:
                reservation_state = workorder._get_reservation_state_for_premix()
            if reservation_state not in ('waiting', 'confirmed', 'assigned'):
                continue
            if reservation_state == 'assigned' and workorder.state == 'waiting':
                workorder.state = 'ready'
            elif reservation_state != 'assigned' and workorder.state == 'ready':
                workorder.state = 'waiting'

    def _get_reservation_state_for_premix(self):
        self.ensure_one()
        reservation_state = False
        if self.production_id.state in ('draft', 'done', 'cancel'):
            return False
        relevant_state = self.production_id.move_raw_ids.with_context(from_mrp=True)._get_relevant_state_among_moves()
        if relevant_state == 'partially_available':
            if self.production_id.workorder_ids.operation_id and self.production_id.bom_id.ready_to_produce == 'asap':
                reservation_state = self.production_id._get_ready_to_produce_state()
            else:
                reservation_state = 'confirmed'
        elif relevant_state != 'draft':
            reservation_state = relevant_state
        return reservation_state

    def action_calculate_batches_produced_quantity(self):
        self.ensure_one()
        for check in self.production_checks_ids:
            not_validated_lines = self.env['quality.check.production.line'].search([
                ('workorder_batch_id', '=', self.current_workorder_batch_id.id),
                ('quality_check_id', '=', check.id),
                ('is_checked', '=', False),
            ])
            if not_validated_lines:
                raise ValidationError(_('Not all lines were validated for this batch!'))
        if not self.current_workorder_batch_id.time_finish:
            self.current_workorder_batch_id.time_finish = fields.Datetime.now()
        self.current_workorder_batch_is_validated = True
        validated_batches = self.workorder_batch_ids.filtered(lambda rec: rec.is_validated)
        self.batches_produced_quantity = sum(validated_batches.mapped('quantity'))

    def action_start_production(self):
        self.ensure_one()
        time_now = fields.Datetime.now()
        self.production_status = 'in_progress'
        self.current_workorder_batch_id.time_start = time_now
        self.current_workorder_batch_check_id.time_start = time_now

    def action_next(self):
        self.ensure_one()
        if self.current_quality_check_premix_line_ids:
            can_validate = not self.current_quality_check_premix_line_ids.filtered(lambda line: not line.is_checked)
            if not can_validate:
                return 0
        if float_compare(self.qty_done, self.component_remaining_qty, precision_rounding=0.01000) != 0:
            raise ValidationError(_('Not all quantity consumed!'))
        current_check = self.current_quality_check_id
        res = super(MrpWorkorder, self).action_next()
        if current_check.test_type in ('register_byproducts', 'register_consumed_materials'):
            current_check.write(self._defaults_from_move(current_check.move_id))
        return res

    def button_change_batch(self):
        self.ensure_one()
        time_now = fields.Datetime.now()
        if not self.current_workorder_batch_id.is_validated:
            raise ValidationError(_('You need to validate this batch first!'))
        if self._context.get('next'):
            self.current_workorder_batch_id = self.next_workorder_batch_id
            if not self.current_workorder_batch_id.time_start:
                self.current_workorder_batch_id.time_start = time_now
        elif self._context.get('previous'):
            self.current_workorder_batch_id = self.previous_workorder_batch_id
        self.current_production_check_id = self.production_checks_ids.sorted('id')[:1]
        if not self.current_workorder_batch_check_id.time_start:
            self.current_workorder_batch_check_id.time_start = time_now
        self.current_production_check_lines_ids = self.env['quality.check.production.line'].search([
            ('quality_check_id', '=', self.current_production_check_id.id),
            ('workorder_batch_id', '=', self.current_workorder_batch_id.id)
        ])

    def button_return_to_the_first_check(self):
        self.ensure_one()
        self.current_production_check_id = self.first_production_check_id
        self.current_production_check_lines_ids = self.env['quality.check.production.line'].search([
            ('quality_check_id', '=', self.current_production_check_id.id),
            ('workorder_batch_id', '=', self.current_workorder_batch_id.id)
        ])

    def button_change_production_check(self):
        self.ensure_one()
        if self._context.get('next'):
            self.current_production_check_id = self.next_production_check_id
            if not self.current_workorder_batch_check_id.time_start:
                self.current_workorder_batch_check_id.time_start = fields.Datetime.now()
        elif self._context.get('previous'):
            self.current_production_check_id = self.previous_production_check_id
        self.current_production_check_lines_ids = self.env['quality.check.production.line'].search([
            ('quality_check_id', '=', self.current_production_check_id.id),
            ('workorder_batch_id', '=', self.current_workorder_batch_id.id)
        ])

    def action_finish_batches(self):
        self.ensure_one()
        if self.production_checks_ids.filtered(lambda rec: rec.quality_state == 'none'):
            raise ValidationError(_('You need to validate all checks!'))
        else:
            if self.workorder_batch_ids.filtered(lambda rec: not rec.is_validated):
                raise ValidationError(_('You need to validate all batches!'))
        self.current_workorder_batch_id = False

    def action_view_production_checks(self):
        self.ensure_one()
        view = self.env.ref('aznut_mrp.quality_check_tree')
        return {
            'name': _('Production Workoder Quality Checks'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'quality.check',
            'views': [(view.id, 'tree')],
            'target': 'current',
            'domain': [('id', 'in', self.production_checks_ids.ids)],
            'context': {'production_workorder_id': self.id}
        }

    def action_reset_lot(self):
        self.ensure_one()
        if self.production_id:
            self.production_id.write({'is_lot_validated': False})

    def action_validate_lot(self):
        self.ensure_one()
        self = self.sudo()
        if self.production_id:
            self.production_id.write({'is_lot_validated': True})

    def action_print(self):
        if self.product_id.uom_id.category_id == self.env.ref('uom.product_uom_categ_unit'):
            qty = int(self.qty_producing)
        else:
            qty = 1

        quality_point_id = self.current_quality_check_id.point_id
        report_type = quality_point_id.test_report_type

        if self.product_id.tracking == 'none':
            xml_id = 'product.action_open_label_layout'
            wizard_action = self.env['ir.actions.act_window']._for_xml_id(xml_id)
            wizard_action['context'] = {'default_product_ids': self.product_id.ids}
            if report_type == 'zpl':
                wizard_action['context'].update({'default_print_format': 'zpl'})
            res = wizard_action
        else:
            if self.finished_lot_id:
                if report_type == 'zpl':
                    xml_id = 'stock.label_lot_template'
                else:
                    xml_id = 'aznut_mrp.action_report_lot_label_inherited'
                value = int(self.env['ir.config_parameter'].sudo().get_param('aznut_mrp.label_per_quantity'))
                labels_count = ceil(qty / value) if value > 0 else qty
                res = self.env.ref(xml_id).report_action([self.finished_lot_id.id] * labels_count)
            else:
                raise UserError(_('You did not set a lot/serial number for '
                                  'the final product'))

        res['id'] = self.env.ref(xml_id).id

        self._next()
        return res

    def action_open_confirm_production_quantity_wizard(self):
        self.ensure_one()
        return {
            'name': _('Confirm Production Quantity'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'confirm.production.quantity.wizard',
            'view_id': self.env.ref('aznut_mrp.confirm_production_quantity_wizard_form').id,
            'target': 'new',
            'context': {
                'default_wizard_production_id': self.production_id.id,
                'default_wizard_workorder_id': self.id,
            }
        }

    def do_finish(self):
        res = super(MrpWorkorder, self).do_finish()
        if self.state == 'done':
            self.duration += self.workcenter_id.cutting_time * self.production_id.batches_count
            self.done_user = self.env.user.id
        if self.production_station:
            quality_station = self.production_id.workorder_ids.filtered("workcenter_id.quality_station")
            self.calculate_next_day_start(quality_station)
        if self.workcenter_id.premix_station:
            production_station = self.production_id.workorder_ids.filtered("workcenter_id.production_station")
            self.calculate_next_day_start(production_station)
        return res

    def calculate_next_day_start(self, workorder):
        for rec in workorder:
            resource_calendar = rec.workcenter_id.resource_calendar_id
            calendar_tz = pytz.timezone(resource_calendar.tz)
            total_week_day = fields.Datetime.now().weekday()
            calendar_day = resource_calendar.attendance_ids.filtered(lambda rec: rec.dayofweek == str(total_week_day))
            hours = calendar_day.mapped('hour_from')
            calendar_day_start = min(hours) if hours else 8
            next_day = fields.Datetime.now() + timedelta(days=1)
            next_day_with_time = calendar_tz.localize(
                next_day.replace(hour=int(calendar_day_start), minute=0, second=0, microsecond=0))
            start_date = next_day_with_time.astimezone(pytz.utc).replace(tzinfo=None)
            duration_expected = rec.duration_expected
            from_date, to_date = rec.workcenter_id._get_first_available_slot(start_date, duration_expected)
            rec.write({
                'date_planned_start': from_date,
                'date_planned_finished': to_date,
            })

    def button_scrap(self):
        self.ensure_one()
        res = super(MrpWorkorder, self).button_scrap()
        if res.get('context'):
            res['context']['product_ids'] = (self.production_id.move_raw_ids.filtered(
                lambda x: x.state != 'cancel') | self.production_id.move_finished_ids.filtered(
                lambda x: x.state == 'done')).mapped('product_id').ids
            res['view_id'] = self.env.ref('aznut_mrp.stock_scrap_form_view2').id
        return res

    def button_finish(self):
        self = self.sudo()
        for wo in self:
            checks = wo.check_ids | wo.production_checks_ids
            block_wo = checks.filtered(lambda rec: rec.quality_state == 'none')
            if block_wo:
                raise ValidationError(_('You need validate all checks'))
            if wo.packaging_station:
                if wo.package_lines_ids.filtered(lambda line: not line.is_validated):
                    raise ValidationError(_('Packages not validated'))
                elif not wo.current_packaging_image_line_ids:
                    raise ValidationError(_('You need to provide current images'))
            if wo.show_number_packages_wizard and wo.state != 'done':
                raise ValidationError(_('Need to set number of packages'))

        res = super(MrpWorkorder, self).button_finish()

        for wo in self.filtered(lambda wo: wo.state == 'done'):
            if wo.premix_station:
                checks = wo.check_ids.filtered(lambda check: check.test_type == 'register_consumed_materials')
                moves = checks.mapped('move_id').filtered(lambda mv: mv.state != 'done' and mv.quantity_done > 0)
                moves._action_done(True)
            wo.write({'done_employees_ids': wo.employees_ids, 'employees_ids': False})
        return res

    def button_start(self):
        self.ensure_one()
        self = self.sudo()
        msg = ''
        production = self.production_id
        wos = production.workorder_ids - self
        not_suitable_wos = wos.filtered(lambda rec: rec.state == 'progress')
        next_wo = production.workorder_ids.filtered(lambda workorder: workorder.state not in ['done', 'cancel'])[:1]

        if self.state != 'progress' and not_suitable_wos:
            msg = 'Operation "%s" is not finished. Please wait!' % ', '.join(not_suitable_wos.mapped('display_name'))
        elif self != next_wo:
            msg = 'Next Workorder Should Be %s' % next_wo.display_name
        if msg:
            raise ValidationError(_(msg))
        if self.workcenter_id.premix_station:
            if self.state != 'progress':
                block_states = ['waiting', 'confirmed', 'partially_available']
                production.action_assign()
                unreserved_lines = production.move_raw_ids.filtered(lambda x: x.state in block_states)
                for line in unreserved_lines:
                    is_deficit = line.product_uom_qty > line.product_id.free_qty
                    is_pack = line.product_id.categ_id.name in categories_to_exclude
                    if is_deficit and not is_pack:
                        raise ValidationError('Some Components Are Not Available!')
        if not self.production_id.is_planned:
            raise ValidationError('Need To Plan This Production Order')
        res = super(MrpWorkorder, self).button_start()
        if self.production_station:
            self.env['mrp.workcenter']._area_cleaning(self.production_id, 'production')
        elif self.packaging_station:
            self.env['mrp.workcenter']._area_cleaning(self.production_id, 'packaging', )
        return res

    @api.model
    def find_workorders_by_employee(self, employee_id):
        wos = self.search([('employees_ids', '=', employee_id), ('state', '!=', 'cancel')])
        wo_names = set([wo_name.upper() for wo_name in wos.mapped('name') if wo_name])
        vals = [{'header': wo_name} for wo_name in wo_names]
        return vals if vals else None

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        res = super(MrpWorkorder, self).search(args, offset=offset, limit=limit, order=order, count=count)
        if isinstance(res, int):
            return res
        else:
            return res.sorted(lambda rec: (rec.product_id.mrp_color is False, int(rec.product_id.mrp_color) if str(
                rec.product_id.mrp_color).isdigit() else float('inf')))

    def _create_checks(self):
        super(MrpWorkorder, self)._create_checks()
        for wo in self:
            checks = wo.check_ids
            priority_checks = checks.filtered(lambda ch: ch.test_type == 'print_label')
            if wo.packaging_station:
                priority_checks |= checks.filtered(lambda ch: ch.test_type == 'worksheet')
            if priority_checks:
                other_checks = checks - priority_checks
                previous_check = self.env['quality.check']
                checks.write({
                    'previous_check_id': False,
                    'next_check_id': False,
                })
                for check in (other_checks | priority_checks):
                    check.previous_check_id = previous_check
                    previous_check.next_check_id = check
                    previous_check = check
                wo._change_quality_check(position='first')

    def _cron_pause_workorders(self):
        workorders = self.env['mrp.workorder'].search([('is_user_working', '=', True)])
        workorders.button_pending()


class MrpWorkorderBatch(models.Model):
    _name = 'mrp.workorder.batch'
    _description = 'MRP Workorder Batch'

    quantity = fields.Float(
        string='Quantity',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
    )
    workorder_id = fields.Many2one(
        'mrp.workorder',
        string='Workorder',
    )
    is_validated = fields.Boolean(
        string='Validated',
    )
    name = fields.Char(
        string='Name',
    )
    time_start = fields.Datetime(
        string='Start Time',
    )
    time_finish = fields.Datetime(
        string='Finish Time',
    )

    time_actual = fields.Float(
        string='Actual Time',
        compute='_compute_time_actual',
    )
    block_reasons_ids = fields.Many2many(
        'mrp.workcenter.productivity',
        string='Block Reasons Records',
        compute='_compute_block_reasons_ids',
    )
    block_reasons_description = fields.Html(
        string='Block Reasons',
        compute='_compute_block_reasons_description',
    )

    @api.depends('time_start', 'time_finish')
    def _compute_block_reasons_ids(self):
        self.block_reasons_ids = False
        for batch in self.filtered(lambda bt: check_is_suitable_for_productivity(bt)):
            block_reasons = batch.workorder_id.block_reasons_ids.filtered(
                lambda br: batch.time_start <= br.date_start <= batch.time_finish)
            batch.block_reasons_ids = block_reasons

    @api.depends('time_start', 'time_finish', 'workorder_id.workcenter_id')
    def _compute_block_reasons_description(self):
        self.block_reasons_description = False
        for batch in self.filtered(lambda bt: bt.block_reasons_ids):
            li_string = ''.join(
                ['<li>%s - %s</li>' % (block_reason.loss_id.name or 'BLOCK', block_reason.duration) for block_reason in
                 batch.block_reasons_ids])
            batch.block_reasons_description = '<ul class="mb-0">%s</ul>' % li_string

    def _compute_time_actual(self):
        self.time_actual = 0
        for batch in self:
            time_start, time_finish = batch.time_start, batch.time_finish or fields.Datetime.now()
            batch.time_actual = get_minutes(time_start, time_finish)


class MrpWorkorderBatchCheck(models.Model):
    _name = 'mrp.workorder.batch.check'
    _description = 'MRP Workorder Batch Check'

    workorder_batch_id = fields.Many2one(
        'mrp.workorder.batch',
        string='Workorder Batch',
    )
    batch_number = fields.Integer(
        string='Batch Number',
        related='workorder_batch_id.id',
    )
    production_check_id = fields.Many2one(
        'quality.check',
        string='Quality Check',
    )
    time_start = fields.Datetime(
        string='Start Time',
    )
    time_finish = fields.Datetime(
        string='Finish Time',
    )
    time_actual = fields.Float(
        string='Actual Time',
        compute='_compute_time_actual',
    )
    is_validated = fields.Boolean(
        string='Validated'
    )
    title = fields.Char(
        'Title',
        related='production_check_id.title',
    )

    def _compute_time_actual(self):
        for batch_check in self:
            time_start, time_finish = batch_check.time_start, batch_check.time_finish or fields.Datetime.now()
            batch_check.time_actual = get_minutes(time_start, time_finish)
