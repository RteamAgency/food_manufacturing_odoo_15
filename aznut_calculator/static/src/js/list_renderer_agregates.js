odoo.define('aznut_calculator.ListRendererAgregates', function (require) {
    "use_strict";

    const ListRenderer = require('web.ListRenderer');
    const {patch} = require('web.utils');

    patch(ListRenderer.prototype, 'aznut_calculator.ListRendererAgregates', {
        _computeAggregates: function () {
            this._super(...arguments);
            const is_list = this.viewType === 'list',
                list_class = this.arch.attrs.class;
            if (is_list && list_class && list_class.includes('powder_active_ingredients')) {
                const col_mg_quantity = this.state.data.reduce((sum, item) => sum + item.data.mg_quantity, 0);
                this.columns.forEach(col => {
                    if (col.attrs.name === 'quantity') {
                        col.aggregate = {
                            help: 'Total',
                            value: col_mg_quantity,
                        }
                    }
                })
            }
        },
    });
});