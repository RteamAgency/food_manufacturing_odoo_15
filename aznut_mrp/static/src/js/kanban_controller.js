odoo.define('aznut_mrp.aznut_mrp_kanban_controller', function (require) {
    "use strict";

    const KanbanController = require('web.KanbanController'),
        core = require('web.core'),
        _t = core._t;

    KanbanController.include({
        renderButtons() {
            this._super.apply(this, arguments);
            if (this.modelName === "mrp.production") {
                const button = this.$buttons.find('.o-kanban-button-new');
                button.after(
                    $('<button class="btn btn-secondary" type="button">' + _t('Unreserve') + '</button>').on('click', async function (e) {
                        const self = this;
                        e.preventDefault();
                        e.stopPropagation();
                        const domain = self.renderer.state.domain;

                        await self._rpc({
                            model: 'mrp.production',
                            method: 'unreserve_from_kanban',
                            args: [[], domain,]
                        })
                        self.trigger_up('reload');
                    }.bind(this)));
                button.after(
                    $('<button class="btn btn-secondary" type="button">' + _t('Reserve') + '</button>').on('click', async function (e) {
                        const self = this;
                        e.preventDefault();
                        e.stopPropagation();
                        const domain = self.renderer.state.domain;

                        await self._rpc({
                            model: 'mrp.production',
                            method: 'reserve_from_kanban',
                            args: [[], domain,]
                        })
                        self.trigger_up('reload');
                    }.bind(this)));
            }
        },
    })
});
