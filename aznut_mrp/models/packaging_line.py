from odoo import models, fields, api


class PackagingImageLine(models.Model):
    _name = 'packaging.image.line'
    _description = 'Packaging Image Line'

    workorder_id = fields.Many2one(
        'mrp.workorder',
        string='Workorder',
    )
    image = fields.Binary(
        string='Image',
        required=True
    )
    name = fields.Char(
        string='Sequence',
        compute='_compute_name',
    )

    @api.depends('workorder_id.current_packaging_image_line_ids')
    def _compute_name(self):
        self.name = False
        for image_line in self:
            image_lines = image_line.workorder_id.current_packaging_image_line_ids
            if image_line in image_lines:
                number = image_lines.mapped('id').index(image_line.id) + 1
                image_line.name = 'Image %s' % number


class PackagingActivityLine(models.Model):
    _name = 'packaging.activity.line'
    _description = 'Packaging Activity Line'

    workorder_id = fields.Many2one(
        'mrp.workorder',
        string='Workorder',
    )
    packaging_activity_id = fields.Many2one(
        'packaging.activity',
        string='Packaging Activity',
        required=True
    )
    activity_employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
    )


class PackagingActivity(models.Model):
    _name = 'packaging.activity'
    _description = 'Packaging Activity'

    _sql_constraints = [
        ('check_name_unique', 'UNIQUE(name)', 'Name must be unique!'),
    ]
    name = fields.Char(
        string='Name',
    )
