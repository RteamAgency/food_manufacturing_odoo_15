from odoo import fields, models, api


def get_not_allowed_test_types_ids(self):
    return self.env.ref('mrp_workorder.test_type_register_consumed_materials') | self.env.ref(
        'mrp_workorder.test_type_register_byproducts')


class SampleTestWizard(models.TransientModel):
    _name = 'sample.test.wizard'
    _description = 'Sample Test Wizard'

    sample_type = fields.Selection(
        [('5_2_lb', '5.2 Lb'),
         ('208_lb', '208 Lb')],
        string='Sample Type',
        required=True,
        default='5_2_lb',
    )
    bom_id = fields.Many2one(
        'mrp.bom',
        string='BoM',
        required=True,
    )
    allowed_boms_ids = fields.Many2many(
        'mrp.bom',
        string='Allowed BoMs',
        required=True,
    )
    quality_points_ids = fields.Many2many(
        'quality.point',
        string='Quality Points',
        compute='_compute_quality_points_ids',
        store=True,
    )
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Workcenter',
        required=True,
        default=lambda self: self.env['mrp.workcenter'].search([('sample_test_station', '=', True)])[:1],
    )
    not_allowed_test_types_ids = fields.Many2many(
        'quality.point.test_type',
        compute="_compute_not_allowed_test_types_ids",
    )
    lead_id = fields.Many2one(
        'crm.lead',
        string='Lead',
        required=True,
        readonly=True,
    )

    @api.depends('workcenter_id')
    def _compute_quality_points_ids(self):
        for wizard in self:
            wizard.quality_points_ids = wizard.workcenter_id.quality_points_ids

    def _compute_not_allowed_test_types_ids(self):
        self.not_allowed_test_types_ids = get_not_allowed_test_types_ids(self)

    def action_confirm(self):
        self.ensure_one()
        product = self.bom_id.product_id or self.bom_id.product_tmpl_id.product_variant_id
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')])[:1]
        MrpProduction = self.env['mrp.production'].with_context(default_picking_type_id=picking_type.id)
        location_id = MrpProduction._get_default_location_src_id()
        location_dest_id = product.with_company(self.env.company).property_stock_production.id
        factor = 0.01 if self.sample_type == '5_2_lb' else 0.4

        mo = MrpProduction.with_context({'is_sample_test_mo': True}).create({
            'product_id': product.id,
            'product_qty': self.bom_id.product_qty * factor,
            'product_uom_id': self.bom_id.product_uom_id.id,
            'move_raw_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_qty * factor,
                'product_uom': line.product_uom_id.id,
                'name': line.product_id.name,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
            }) for line in self.bom_id.bom_line_ids],
        })

        self.env['mrp.workorder'].create({
            'workcenter_id': self.workcenter_id.id,
            'product_id': product.id,
            'quality_point_ids': self.quality_points_ids.ids,
            'name': 'Sample Test',
            'product_uom_id': self.bom_id.product_uom_id.id,
            'production_id': mo.id,
        })
        mo._create_update_move_finished()
        self.lead_id.sample_test_orders_ids |= mo
        return {
            'name': 'Production',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'form',
            'view_id': self.env.ref('mrp.mrp_production_form_view').id,
            'res_id': mo.id,
            'target': 'current',
        }
