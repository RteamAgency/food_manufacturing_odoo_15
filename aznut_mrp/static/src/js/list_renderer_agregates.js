odoo.define('aznut_mrp.ListRendererAgregates', function (require) {
    "use_strict";
    
    const ListRenderer = require('web.ListRenderer');
    const { patch } = require('web.utils');
    
    patch(ListRenderer.prototype, 'aznut_mrp.ListRendererAgregates', {
        /**
         * @override
         */
        _computeAggregates: function () {
            this._super(...arguments);
            const is_list = this.viewType === 'list',
                list_class = this.arch.attrs.class;
            if (is_list && list_class && list_class.includes('azn_sale_order')) {
                const col_margin = this.columns.filter(col => col.attrs.name === 'margin'),
                    col_amount = this.state.data.reduce((sum, item) => sum + item.data.amount_untaxed, 0),
                    col_production_margin = this.columns.filter(col => col.attrs.name === 'production_margin'),
                    col_production_lines = this.state.data.filter(item => item.data.show_production_margin),
                    col_production_amount = col_production_lines.reduce((sum, item) => sum + item.data.amount_untaxed, 0);
                if (col_amount) {
                    if (col_margin[0]) {
                        const total_percent = col_margin[0].aggregate.value / col_amount * 100;
                        if (total_percent > 0) {
                            this.columns.forEach(col => {
                                if (col.attrs.name === 'margin_percent') {
                                    col.aggregate = {
                                        help: 'Total Margin %',
                                        value: parseFloat(total_percent.toFixed(2)) / 100,
                                    }
                                }
                            })
                        }
                    }
                }
                if (col_production_amount) {
                    if (col_production_margin[0]) {
                        const total_percent = col_production_margin[0].aggregate.value / col_production_amount * 100;
                        if (total_percent > 0) {
                            this.columns.forEach(col => {
                                if (col.attrs.name === 'production_margin_percent') {
                                    col.aggregate = {
                                        help: 'Total Production Margin %',
                                        value: parseFloat(total_percent.toFixed(2)) / 100,
                                    }
                                }
                            })
                        }
                    }
                }
            }
        },
        _renderBodyCell: function (record, node, colIndex, options) {
            var $cell = this._super.apply(this, arguments);
            const name = node.attrs.name,
                  field = this.state.fields[name],
                  prefix = (field && field.string) ? `${field.string}: `  : '';
            if (prefix && $cell) {
                const prev_title = $cell.attr('title');
                if (prev_title) {
                    $cell.attr('title', prefix + prev_title)
                }
                if (prefix && !prev_title){
                    $cell.attr('title', prefix.slice(0, -2))
                }
            }
            return $cell
        },
    });
});