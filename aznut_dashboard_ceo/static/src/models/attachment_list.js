/** @odoo-module **/

import {
    registerFieldPatchModel,
    registerInstancePatchModel,
    registerIdentifyingFieldsPatch,
} from'@mail/model/model_core';
import { clear, replace } from '@mail/model/model_field_command';
import { one2one } from '@mail/model/model_field';

registerFieldPatchModel('mail.attachment_list', 'aznut_dashboard_ceo/static/src/models/activity.js', {
    dashboard_activity: one2one('mail.activity', {
        inverse: 'attachmentList',
        readonly: true,
    }),
});

registerInstancePatchModel('mail.attachment_list', 'aznut_dashboard_ceo/static/src/models/activity.js', {
    _computeAttachments() {
        if (this.message) {
            return replace(this.message.attachments);
        }
        if (this.chatter && this.chatter.thread) {
            return replace(this.chatter.thread.allAttachments);
        }
        if (this.composerView && this.composerView.composer) {
            return replace(this.composerView.composer.attachments);
        }
        if (this.dashboard_activity){
            return replace(this.dashboard_activity.dashboard_attachment_ids);
        }
        return clear();
    },
});

registerIdentifyingFieldsPatch('mail.attachment_list', 'aznut_dashboard_ceo/static/src/models/activity.js', identifyingFields => {
    identifyingFields[0].push('dashboard_activity');
});
