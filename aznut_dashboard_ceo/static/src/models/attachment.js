/** @odoo-module **/

import { registerFieldPatchModel } from'@mail/model/model_core';
import { many2many } from '@mail/model/model_field';

registerFieldPatchModel('mail.attachment', 'aznut_dashboard_ceo/static/src/models/activity.js', {
    dashboard_activities: many2many('mail.activity', {
        inverse: 'dashboard_attachment_ids',
    }),
});
