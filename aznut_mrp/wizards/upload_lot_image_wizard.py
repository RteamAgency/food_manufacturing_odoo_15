from odoo import fields, models


class UploadLotImageWizard(models.TransientModel):
    _name = 'upload.lot.image.wizard'
    _description = 'Upload Lot Image Wizard'

    image_1920 = fields.Image(
        string="Image",
        max_width=1920,
        max_height=1920,
        required=True,
    )
    lot_id = fields.Many2one(
        'stock.production.lot',
        string='Lot',
        readonly=True,
        required=True,
    )

    def action_confirm(self):
        attachment = self.env['ir.attachment'].create({
            'name': 'Image',
            'type': 'binary',
            'datas': self.image_1920,
            'res_model': 'stock.production.lot',
            'res_id': self.lot_id.id,
            'mimetype': 'image/png',
        })

        message_body = f"""
            <p>{fields.Datetime.now()}:</p>
            <img src="/web/content/{attachment.id}" alt="Image"/>
        """
        self.lot_id.message_post(body=message_body, subtype_xmlid='mail.mt_note')
