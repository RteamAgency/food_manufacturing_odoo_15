/** @odoo-module **/

import FormRenderer from 'web.FormRenderer';
import { bus } from 'web.core';


FormRenderer.include({
    events: _.extend({}, FormRenderer.prototype.events, {
        'click .btn-metal-detector': '_onMetalDetectorClick',
    }),
    _onMetalDetectorClick: function(ev) {
        bus.trigger('open_video_dialog_manually', {workorderId: this.state.res_id});
    }
})
