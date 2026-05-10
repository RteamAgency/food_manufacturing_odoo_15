odoo.define('aznut_mrp.open_wizard_on_click', function (require) {
    "use strict";

    const ListRenderer = require('web.ListRenderer');

    ListRenderer.include({
        _onRowClicked: function (event) {
            event.stopPropagation();
            const target = event.target;
            const recordId = target.closest('tr').getAttribute('data-id'),
                line = this.state.data.filter(item => item.id === recordId);
            if (target.getAttribute('name') === 'container_number' && line[0]) {
                this.do_action({
                    name: 'Put Container Number',
                    type: 'ir.actions.act_window',
                    view_mode: 'form',
                    views: [[false, 'form']],
                    res_model: 'put.container.number.wizard',
                    target: 'new',
                    context: {
                        'default_premix_quality_check_line_id': line[0].res_id,
                    }
                });
            } else {
                this._super.apply(this, arguments);
            }
        },
    });
});
