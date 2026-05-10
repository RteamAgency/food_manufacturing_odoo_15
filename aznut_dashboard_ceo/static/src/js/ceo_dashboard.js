odoo.define('aznut_dashboard_ceo.Dashboard', function (require) {
    "use strict";
    
    var AbstractAction = require('web.AbstractAction');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var QWeb = core.qweb;

    const block_mapping = {
        'sales_simple': ['Sales', 'fa fa-line-chart'],
        'production_simple': ['Production', 'fa fa-wrench'],
        'customer_answers': ['CRM', 'fa fa-users'],
        'schedule_orders': ['Schedule Orders', 'fa fa-calendar'],
        'packaging_simple': ['Packaging', 'fa fa-dropbox'],
        'batch_availability': ['Batch Availability', ''],
        'batch_records_15_min': ['Batch +15 min', ''],
        'inventory_simple': ['Inventory', 'fa fa-cubes'],
        'sales_diagram': ['By Brands Ordered', 'fa fa-bar-chart'],  
    }

    var DynamicDashboard = AbstractAction.extend({
        template: 'CeoDashboard',
        events: {
            'click .not_available_components': '_onClickNotAvailableComponents',
            'click .yesterday_15_min': '_onClickBatchMinutes',
            'click .month_15_min': '_onClickBatchMinutes',
            'click .schedule_mo': '_onClickScheduledMo',
            'click .waiting_leads': '_onClickWaitingAnswers',
            'click .create_activity': '_onClickCreateActivity',
            'click .urgent_activities': '_onClickUrgentActivities',
            'click .open_inv': '_onClickOpenInvoice',
        },
    
        init: function(parent, context) {
            this.action_id = context['id'];
            this._super(parent, context);
            this.block_ids = []
        },
    
        start: function() {
            var self = this;
            this.set("title", 'Dashboard');
            return this._super().then(function() {
                self.render_dashboards();
            });
        },
    
        willStart: function() {
            var self = this;
            return $.when(ajax.loadLibs(this), this._super()).then(function() {
                 return self.fetch_data();
            });
        },
    
        fetch_data: function() {
            var self = this;
            var def1 =  this._rpc({
                    route: '/ceo_dashboard/get_data'
                }).then(function(result) {
                    self.blocks = result;
            });
            return $.when(def1);
        },
        
        prepare_bars_dataset: function(chart_data) {
            const rows = chart_data.data;
            const totalQuantity = rows.reduce((sum, row) => sum + row[1], 0);
            const totalAmount = rows.reduce((sum, row) => sum + row[2], 0);

            const grouped = {};
            const sortedRows = rows.sort((a, b) => {
                const sumA = a[1] + a[2];
                const sumB = b[1] + b[2];
                return sumA - sumB;
            });
            sortedRows.forEach(([label, quantity, amount]) => {
                const quantityRatio = quantity / totalQuantity;
                const amountRatio = amount / totalAmount;
                const key = (quantityRatio < 0.05 && amountRatio < 0.05) ? null : (label ?? null);
        
                if (!grouped[key]) {
                    grouped[key] = [0, 0];
                }
        
                grouped[key][0] += quantity;
                grouped[key][1] += amount;
            });
            if (grouped[null]) {
                grouped['Other'] = grouped[null];
                delete grouped[null];
            }
            const finalLabels = Object.keys(grouped);
            const finalQuantities = finalLabels.map(label => Number(grouped[label][0].toFixed(2)));
            const finalAmounts = finalLabels.map(label => Number(grouped[label][1].toFixed(2)));
            return {finalLabels, finalQuantities, finalAmounts }
        },

        parseFloatTime: function(floatTime) {
            if (!floatTime) return '0:00';
            
            const totalSeconds = Math.round(+floatTime * 60); // 1 floatTime = 1 минута
            const totalMinutes = Math.floor(totalSeconds / 60);
            const hours = Math.floor(totalMinutes / 60);
            const minutes = totalMinutes % 60;

            return `${hours}:${minutes.toString().padStart(2, '0')}`;
        },

        handleAction: async function({ model, method, args = [], config = {} }) {
            const self = this;
            const {
                name = '',
                view_mode = 'list',
                res_model = '',
                target = 'current',
                context = {},
                res_id = undefined,
            } = config;

            const result = await self._rpc({ model, method, args });

            if (!result?.action) return;

            self.do_action({
                name,
                type: 'ir.actions.act_window',
                view_mode,
                views: [[result.action.view_id, view_mode], [false, 'form']],
                res_model,
                target,
                domain: result.action.domain,
                context: {
                    ...context,
                },
                res_id,
            });
        },

        getResIds: function (ev) {
            const ids = ev?.target?.closest('li')?.dataset?.resIds || '';
            return ids.split(',').filter(Boolean).map(Number);
        },

        _onClickNotAvailableComponents: function() {
            return this.handleAction({
                model: 'purchase.order',
                method: 'generate_not_available_components',
                config: {
                    name: 'Not Available Components',
                    res_model: 'product.product',
                },
            });
        },

        _onClickBatchMinutes: function(ev) {
            const res_ids = this.getResIds(ev);
            if (!res_ids.length) return;
            return this.handleAction({
                model: 'mrp.workorder.batch',
                method: 'generate_batch_action',
                args: [res_ids],
                config: {
                    name: 'Batch Records over 15 min',
                    res_model: 'mrp.workorder.batch',
                },
            });
        },

        _onClickScheduledMo: function(ev) {
            const res_ids = this.getResIds(ev);
            if (!res_ids.length) return;
            return this.handleAction({
                model: 'mrp.production',
                method: 'generate_shedule_mo_action',
                args: [res_ids],
                config: {
                    name: 'Scheduled MOs',
                    res_model: 'mrp.production',
                },
            });
        },

        _onClickWaitingAnswers: function(ev) {
            const res_ids = this.getResIds(ev);
            if (!res_ids.length) return;
            return this.handleAction({
                model: 'crm.lead',
                method: 'generate_waiting_answers_action',
                args: [res_ids],
                config: {
                    name: 'Customers Without Answers',
                    res_model: 'crm.lead',
                    view_mode: 'kanban',
                },
            });
        },

        _onClickCreateActivity: async function() {
            const result = await this._rpc({
                model: 'mail.activity',
                method: 'get_dashboard_activity_action',
            });

            if (result?.action) {
                this.do_action({
                    name: 'Schedule Activity',
                    type: 'ir.actions.act_window',
                    view_mode: 'form',
                    views: [[result.action.view_id, 'form']],
                    res_model: 'mail.activity',
                    target: 'new',
                    res_id: false,
                    context: {
                        default_importance_level: 'normal',
                        default_res_model: 'hr.employee',
                        is_dashboard_action: true,
                    },
                });
            }
        },

        _onClickUrgentActivities: function(ev) {
            return this.handleAction({
                model: 'dashboard.mail.activity',
                method: 'generate_urgent_activities_action',
                args: [],
                config: {
                    name: 'Urgent Activities',
                    res_model: 'dashboard.mail.activity',
                    context: {group_by: "state"}
                },
            });
        },

        _onClickOpenInvoice: function(ev) {
            const res_ids = this.getResIds(ev);
            if (!res_ids.length) return;

            return this.handleAction({
                model: 'account.move',
                method: 'generate_open_invoice_action',
                args: [res_ids],
                config: {
                    name: 'Open Invoices',
                    res_model: 'account.move',
                },
            });
        },

        render_dashboards: function () {
            const self = this;
            const container = self.$('.o_ceo_dashboard .stats-container');

            const renderBlock = (template, context) => {
                const rendered = QWeb.render(template, context);
                container.append(rendered);
            };

            const sorted_blocks = Object.entries(self.blocks).sort(
                ([keyA], [keyB]) => {
                    const order = Object.keys(block_mapping);
                    return order.indexOf(keyA) - order.indexOf(keyB);
                }
            );
            
            sorted_blocks.forEach(([key, value]) => {
                const [title, icon] = block_mapping[key];

                if (key === 'sales_diagram') {
                    renderBlock('CeoDashboardSaleBarChart', { icon, block_data: value });

                    value.forEach(chart_data => {
                        if (chart_data?.data) {
                            const { finalLabels, finalQuantities, finalAmounts } = self.prepare_bars_dataset(chart_data);
                            const data = {
                                labels: finalLabels,
                                datasets: [
                                    {
                                        label: 'Quantity, Jars',
                                        data: finalQuantities,
                                        borderColor: 'rgba(54, 162, 235, .5)',
                                        backgroundColor: 'rgba(54, 162, 235, .2)',
                                        borderWidth: 2,
                                    },
                                    {
                                        label: 'Amount, $',
                                        data: finalAmounts,
                                        borderColor: 'rgba(255, 99, 132, .5)',
                                        backgroundColor: 'rgba(255, 99, 132, .2)',
                                        borderWidth: 2,
                                    }
                                ]
                            };
                            const chart_config = {
                                type: 'bar',
                                data,
                                options: {
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    title: {
                                        display: true,
                                        text: chart_data.title,
                                    },
                                    tooltips: {
                                        callbacks: {
                                            label: function(tooltipItem, data) {
                                                const datasetLabel = data.datasets[tooltipItem.datasetIndex].label || '';
                                                const value = tooltipItem.yLabel.toLocaleString();
                                                return `${datasetLabel}: ${value}`;
                                            }
                                        }
                                    },
                                    scales: {
                                        yAxes: [{
                                            ticks: { 
                                                maxTicksLimit: 5,
                                                fontSize: 13,
                                                callback: function(value) {
                                                    return value.toLocaleString();
                                                }
                                            },
                                        }],
                                        xAxes: [{
                                            ticks: { 
                                                fontSize: 13,
                                            },
                                        }],
                                    }
                                }
                            };
                            const context = self.$(`.o_ceo_dashboard #${chart_data.chart_id}`)[0]?.getContext('2d');
                            if (context) new Chart(context, chart_config);
                        }
                    });

                } else if (key === 'batch_availability' || key === 'batch_records_15_min') {
                    renderBlock('CeoDashboardMiniBlock', { title, icon, block_data: value });
                }  else if (key === 'customer_answers') {
                    renderBlock('CeoDashboardCrmBlock', { title, icon, block_data: value });
                } else {
                    const block_data = (key === 'packaging_simple')
                        ? value.map(item => {
                            item.data[1] = self.parseFloatTime(item.data[1]);
                            return item;
                        })
                        : value;

                    renderBlock('CeoDashboardSimpleBlock', { title, icon, block_data });
                }
            });
        }
    });
    
    
    core.action_registry.add('dynamic_dashboard', DynamicDashboard);
    
    return DynamicDashboard;
});
