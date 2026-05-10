from odoo import fields, models, api, _

from ..wizard.sample_test_wizard import get_not_allowed_test_types_ids


def get_quality_wo(mrp):
    quality_wo = mrp.workorder_ids.filtered(lambda wo: wo.workcenter_id.quality_station)[:1]
    if not quality_wo:
        quality_wo = mrp.workorder_ids.filtered(lambda wo: wo.workcenter_id.sample_test_station)[:1]
    return quality_wo


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    sample_test_station = fields.Boolean(
        string='Sample Test Station',
    )
    quality_points_ids = fields.Many2many(
        'quality.point',
        string='Quality Points',
    )
    not_allowed_test_types_ids = fields.Many2many(
        'quality.point.test_type',
        compute="_compute_not_allowed_test_types_ids",
    )

    def _compute_not_allowed_test_types_ids(self):
        self.not_allowed_test_types_ids = get_not_allowed_test_types_ids(self)

    @api.onchange('sample_test_station')
    def _onchange_sample_test_station(self):
        if not self.sample_test_station:
            self.quality_points_ids = False


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    sample_test_station = fields.Boolean(
        related='workcenter_id.sample_test_station',
    )
    sample_test_workorder_line_ids = fields.One2many(
        'sample.test.workorder.line',
        'workorder_id',
        string='Sample Test Workorder Line',
    )
    show_sample_test_workorder_lines = fields.Boolean(
        string='Show Sample Test Workorder Lines',
        compute='_compute_show_sample_test_workorder_lines',
    )

    def _create_checks(self):
        super(MrpWorkorder, self)._create_checks()
        for workorder in self.filtered(lambda wo: wo.workcenter_id.sample_test_station):
            checks = workorder.check_ids
            worksheet_checks = checks.filtered(lambda ch: ch.test_type == 'worksheet')
            if worksheet_checks:
                other_checks = checks - worksheet_checks
                previous_check = self.env['quality.check']
                checks.write({
                    'previous_check_id': False,
                    'next_check_id': False,
                })
                for check in (other_checks | worksheet_checks):
                    check.previous_check_id = previous_check
                    previous_check.next_check_id = check
                    previous_check = check
                workorder._change_quality_check(position='first')

    @api.depends('operation_id')
    def _compute_quality_point_ids(self):
        for workorder in self:
            if not workorder.workcenter_id.sample_test_station:
                quality_points = workorder.operation_id.quality_point_ids
                quality_points = quality_points.filtered(
                    lambda qp: (not qp.product_ids or workorder.production_id.product_id in qp.product_ids) and (
                            qp.company_id == workorder.company_id))
                workorder.quality_point_ids = quality_points
            else:
                workorder.quality_point_ids = workorder.quality_point_ids or False

    @api.depends('workcenter_id.sample_test_station', 'check_ids.quality_state')
    def _compute_show_sample_test_workorder_lines(self):
        self.show_sample_test_workorder_lines = False
        for workorder in self:
            if workorder.sample_test_station and not workorder.skipped_check_ids:
                workorder.show_sample_test_workorder_lines = True


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    sample_test_lead_id = fields.Many2one(
        'crm.lead',
        compute="_compute_sample_test_lead_id",
        string="Sample Test Opporunity",
        compute_sudo=True,
    )
    
    def _compute_sample_test_lead_id(self):
        for rec in self:
            lead = self.env["crm.lead"].search([('sample_test_orders_ids', 'in', [rec.id])], limit=1)
            rec.sample_test_lead_id = lead.id if lead else False
    
    def action_confirm(self):
        res = super(MrpProduction, self).action_confirm()
        self._prepare_sample_test()
        return res

    def _prepare_sample_test(self):
        for sample_test_wo in self.mapped('workorder_ids').filtered(lambda wo: wo.workcenter_id.sample_test_station):
            sample_test_wo.write({
                'sample_test_workorder_line_ids': [(0, 0, {
                    'move_id': mv.id,
                    'workorder_id': sample_test_wo.id,
                }) for mv in sample_test_wo.move_raw_ids]
            })

    def _get_analyses_data(self):
        self = self.sudo()
        products = self.move_raw_ids.product_id
        quality_check = []
        check_status = False
        worksheet_images = {}
        active_category = self.env['product.category'].search([('name', 'ilike', 'Active Ingredients')], limit=1)
        base_category = self.env['product.category'].search([('name', 'ilike', 'Base Ingredients')], limit=1)
        child_active_categories = self.env['product.category'].search([('id', 'child_of', active_category.id)])
        child_base_categories = self.env['product.category'].search([('id', 'child_of', base_category.id)])
        base_ingredients = products.filtered(lambda rec: rec.categ_id.id in child_base_categories.ids)
        active_ingredients = products.filtered(lambda rec: rec.categ_id.id in child_active_categories.ids)
        quality_wo = get_quality_wo(self)
        production_wo = self.workorder_ids.filtered(lambda wo: wo.workcenter_id.production_station)
        analyses_data = {}
        workorders_operators = {}
        packaging_wo = self.workorder_ids.filtered(lambda wo: wo.workcenter_id.packaging_station)[:1]
        packaging_images = []
        packaging_images_count = max([
            len(packaging_wo.current_packaging_image_line_ids),
            len(packaging_wo.previous_packaging_image_lines_ids),
        ])

        for number in range(packaging_images_count):
            previous_image, current_image = False, False
            if number < len(packaging_wo.current_packaging_image_line_ids):
                current_image = packaging_wo.current_packaging_image_line_ids[number].image
            if number < len(packaging_wo.previous_packaging_image_lines_ids):
                previous_image = packaging_wo.previous_packaging_image_lines_ids[number].image
            packaging_images.append({'current_image': current_image, 'previous_image': previous_image})

        for workorder in self.workorder_ids:
            workorders_operators.update({workorder.name: ', '.join(workorder.mapped('done_employees_ids.name'))})

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

        if quality_wo:
            analyses_data = {}
            check_template = quality_wo.check_ids.worksheet_template_id.model_id.model
            checks = quality_wo.check_ids.filtered(lambda ch: ch.test_type == 'worksheet')
            states = [check.quality_state for check in checks]

            if all(state == 'pass' for state in states):
                check_status = 'pass'
            elif all(state == 'fail' for state in states):
                check_status = 'fail'
            else:
                check_status = 'none'
            for check in checks:
                quality_worksheet = self.env[check_template].search([('x_quality_check_id', '=', check.id)])
                if quality_worksheet:
                    worksheet_fields = quality_worksheet.fields_get()
                    binary_fields = {i: y.get('string') for i, y in worksheet_fields.items() if
                                     y.get('type') == 'binary'}
                    worksheet_images = {y: quality_worksheet.__getattribute__(i) for i, y in binary_fields.items() if
                                        quality_worksheet.__getattribute__(i)}

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

    def _get_bom_structure_data(self):
        res = super(MrpProduction, self)._get_bom_structure_data()
        base_lines, active_lines = res.get('base_lines'), res.get('active_lines')

        sample_test_wo = self.workorder_ids.filtered(lambda rec: rec.workcenter_id.sample_test_station)
        if sample_test_wo:
            for line in sample_test_wo.check_ids.filtered(lambda ch: ch.test_type == 'register_consumed_materials'):
                if line.component_id.categ_id.name == 'Base ingredients':
                    lots = line.move_id.lot_ids
                    base_lines.append({'bom_line': line.move_id, 'lot': lots if lots else None})
                elif line.component_id.categ_id.name == 'Active ingredients':
                    lots = line.move_id.lot_ids
                    active_lines.append({'bom_line': line.move_id, 'lot': lots if lots else None})
        res.update({
            'base_lines': base_lines,
            'active_lines': active_lines,
        })

        return res

    @api.model
    def create(self, values):
        if self.env.context.get('is_sample_test_mo', False):
            sequence_id = self.env.ref('aznut_calculator.seq_sample_test_production')
            values['name'] = sequence_id.next_by_id() or _('New')
        return super(MrpProduction, self).create(values)
    
    def button_open_crm_lead(self):
        self.ensure_one()
        return {
            'name': 'Opportunity',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.sample_test_lead_id.id,
            'view_mode': 'form',
            'view_id': self.env.ref('crm.crm_lead_view_form').id,
        }
