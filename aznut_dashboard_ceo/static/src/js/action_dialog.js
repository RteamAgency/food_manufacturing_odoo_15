/** @odoo-module **/

import { ActionDialog } from "@web/webclient/actions/action_dialog";
import { patch } from 'web.utils';

patch(ActionDialog.prototype, 'aznut_dashboard_ceo.ActionDialog', {
    mounted() {
        this._super();
        const is_activity_dialog = document.querySelector('.dashboard-activity');
        if (is_activity_dialog) {
            const dialog_wrap = is_activity_dialog.closest('.modal-dialog');
            dialog_wrap.classList.add('dashboard-activity-wrap')
        }
    }
});
