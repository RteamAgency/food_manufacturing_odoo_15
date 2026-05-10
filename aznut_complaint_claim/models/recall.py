from odoo import models, fields, api

RECALL_DICT = {
    'first_class': 'a situation in which there is a reasonable probability that the use of or exposure to a violative product will cause serious adverse health consequences or death.',
    'second_class': 'a situation in which use of or exposure to a violative product may cause temporary or medically reversible adverse health consequences or where the probability of serious adverse health consequences is remote.',
    'third_class': 'a situation in which use of or exposure to a violative product is not likely to cause adverse health consequences.',
}

RECALL_CLASSES = [
    ('first_class', 'Class I'),
    ('second_class', 'Class II'),
    ('third_class', 'Class III'),
]


class Recall(models.Model):
    _name = 'recall.recall'
    _description = 'Recall'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Name',
        readonly=True,
    )
    lot_id = fields.Many2one(
        string='Lot',
        related='production_id.lot_producing_id'
    )
    product_id = fields.Many2one(
        related='lot_id.product_id',
    )
    production_id = fields.Many2one(
        'mrp.production',
        string='Production',
        required=True,
        readonly=True,
    )
    moves_ids = fields.Many2many(
        'stock.move',
        compute="_compute_moves_ids",
    )
    recall_status = fields.Selection(
        [('open', 'Open'), ('closed', 'Closed')],
        string='Recall Status',
        default='open',
        required=True,
    )
    recall_class = fields.Selection(
        RECALL_CLASSES,
        string='Recall Class',
        required=True,
        default='first_class',
    )
    recall_class_description = fields.Char(
        string='Recall Class Description',
        compute='_compute_recall_class_description',
    )

    @api.depends('recall_class')
    def _compute_recall_class_description(self):
        for recall in self:
            recall.recall_class_description = RECALL_DICT[recall.recall_class]

    @api.depends('production_id')
    def _compute_moves_ids(self):
        for recall in self:
            recall.moves_ids = recall.production_id.move_raw_ids.filtered(lambda mv: mv.quantity_done)

    @api.model
    def create(self, vals):
        if 'name' not in vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('recall.recall') or 'New'
        return super(Recall, self).create(vals)
