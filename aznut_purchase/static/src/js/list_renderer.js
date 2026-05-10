odoo.define('aznut_purchase.open_product_forecast', function (require) {
    "use strict";

    const ListRenderer = require('web.ListRenderer');

    ListRenderer.include({
        events: Object.assign({}, ListRenderer.prototype.events, {
            'click .product_forecast_link': '_onProductForecastLinkCLick',
            'click #by_brand_current': '_onForecastBrandCLick',
            'click #by_brand_next': '_onForecastBrandCLick',
            'click #by_component_current': '_onForecastComponentsCLick',
            'click #by_component_next': '_onForecastComponentsCLick',
        }),
        _onProductForecastLinkCLick: async function (event) {
            event.stopPropagation();
            const target = event.target;
            const recordId = target.closest('tr').getAttribute('data-id'),
                line = this.state.data.filter(item => item.id === recordId);
            if (target.classList.contains('product_forecast_link') && line[0]) {
                const action = await this._rpc({
                    model: 'product.product',
                    method: 'action_product_product_forecast_report',
                    args: [line[0].data.id],
                })
                action.context = {
                    'active_model': 'product.product',
                    'active_id': line[0].data.id,
                }
                this.do_action(action);
            }
        },
        _onForecastBrandCLick: async function (event) {
            event.stopPropagation();
            const target = event.target;
            const action = await this._rpc({
                model: 'purchase.jars.brand.report',
                method: 'get_report_action',
                args: []
            })
            if (target.id === 'by_brand_next') {
                action.context['for_next_month_brand'] = true
            }
            this.do_action(action);
        },
        _onForecastComponentsCLick: async function (event) {
            event.stopPropagation();
            const target = event.target;
            const action = await this._rpc({
                model: 'purchase.jars.components.report',
                method: 'get_report_action',
                args: []
            })
            if (!action) {
                this.call('notification', 'notify', {
                    message: 'Please set up the necessary components for reporting.',
                    type: 'danger'
                })
                return
            }
            if (target.id === 'by_component_next') {
                action['context'] = {
                    'for_next_month_component': true,
                }
            }
            this.do_action(action);
        },
    })
});
