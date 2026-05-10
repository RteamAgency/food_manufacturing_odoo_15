/** @odoo-module **/

import {
    registerClassPatchModel,
    registerFieldPatchModel,
    registerInstancePatchModel,
} from'@mail/model/model_core';
import { clear, insertAndReplace, unlinkAll } from '@mail/model/model_field_command';
import { attr, many2many, one2one } from '@mail/model/model_field';

registerFieldPatchModel('mail.activity', 'aznut_dashboard_ceo/static/src/models/activity.js', {
    importance_level: attr({
        default: false,
    }),
    dashboard_attachment_ids: many2many('mail.attachment', {
        inverse: 'dashboard_activities',
    }),
    attachmentList: one2one('mail.attachment_list', {
        compute: '_computeAttachmentList',
        inverse: 'dashboard_activity',
        isCausal: true,
        readonly: true,
    }),
});

registerClassPatchModel('mail.activity', 'aznut_dashboard_ceo/static/src/models/activity.js', {
    convertData(data) {
        const res = this._super(data);
        if ('importance_level' in data)  {
            res.importance_level = data.importance_level;
        }
        if ('dashboard_attachment_ids' in data) {
            if (data.dashboard_attachment_ids.length == 0) {
                res.dashboard_attachment_ids = unlinkAll();
            } else {
                res.dashboard_attachment_ids = insertAndReplace(data.dashboard_attachment_ids.map(attachmentData =>
                    this.messaging.models['mail.attachment'].convertData(attachmentData)
                ));
            }
        }
        return res;
    },
});

registerInstancePatchModel('mail.activity', 'aznut_dashboard_ceo/static/src/models/activity.js', {
    _computeAttachmentList() {
        if (this.dashboard_attachment_ids.length > 0) {
            return insertAndReplace()
        } else {
            return clear()
        }
    }
});
