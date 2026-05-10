odoo.define('aznut_purchase.dashboard', function (require) {
    "use strict";

    const {PurchaseListDashboardRenderer, PurchaseKanbanDashboardRenderer} = require('purchase.dashboard');
    const core = require('web.core');
    const QWeb = core.qweb;


    PurchaseListDashboardRenderer.include({
        _onDashboardActionClicked: function (e) {
            e.preventDefault();
            const self = this,
                $action = $(e.currentTarget),
                context = JSON.parse($action.attr('context'));
            if (context.not_available_batches === true) {
                this._rpc({
                    model: 'purchase.order',
                    method: 'generate_not_available_components',
                }).then(function (result) {
                    if (result.action) {
                        self.do_action({
                            name: 'Not Available Components',
                            type: 'ir.actions.act_window',
                            view_mode: 'list',
                            views: [[result.action.view_id, 'list']],
                            res_model: 'product.product',
                            target: 'current',
                            domain: result.action.domain,
                            context: {
                                'create': 0,
                                'write': 0,
                                'delete': 0,
                            }
                        });
                    }
                });
            } else if (context.purchase_accelerator === true) {
                self.do_action({
                    name: 'Purchase Accelerator',
                    type: 'ir.actions.act_window',
                    view_mode: 'form',
                    views: [[false, 'form']],
                    res_model: 'purchase.accelerator.wizard',
                    target: 'new',
                });
            } else if (context.receiving_operator === true) {
                self.do_action('aznut_purchase.purchase_rfq_receiving_operator_buttons',
                    {additional_context: context});
            } else {
                this._super(...arguments);
            }
        },
    })

    PurchaseKanbanDashboardRenderer.include({
        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var values = self.state.dashboardValues;
                var purchase_dashboard = QWeb.render('purchase.PurchaseDashboard', {
                    values: values,
                });
                self.$el.parent().find(".o_purchase_dashboard").remove();
                self.$el.prepend(purchase_dashboard);
            });
        },

        _onDashboardActionClicked: function (e) {
            e.preventDefault();
            debugger;
            const self = this,
                $action = $(e.currentTarget),
                context = JSON.parse($action.attr('context'));
            if (context.not_available_batches === true) {
                this._rpc({
                    model: 'purchase.order',
                    method: 'generate_not_available_components',
                }).then(function (result) {
                    if (result.action) {
                        self.do_action({
                            name: 'Not Available Components',
                            type: 'ir.actions.act_window',
                            view_mode: 'list',
                            views: [[result.action.view_id, 'list']],
                            res_model: 'product.product',
                            target: 'current',
                            domain: result.action.domain,
                            context: {
                                'create': 0,
                                'write': 0,
                                'delete': 0,
                            }
                        });
                    }
                });
            } else if (context.purchase_accelerator === true) {
                self.do_action({
                    name: 'Choose Ingredients Quantity',
                    type: 'ir.actions.act_window',
                    view_mode: 'form',
                    views: [[false, 'form']],
                    res_model: 'purchase.accelerator.wizard',
                    target: 'new',
                });
            } else {
                this._super(...arguments);
            }
        },
    })
})
