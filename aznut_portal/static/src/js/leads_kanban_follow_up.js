odoo.define('aznut.portal.leads.kanban', function (require) {
    "use strict";

    let KanbanController = require('web.KanbanController');
    let KanbanView = require('@crm/js/crm_kanban')[Symbol.for("default")].CrmKanbanView;

    let viewRegistry = require('web.view_registry');


    function renderFollowUpButton() {
        if (this.$buttons) {
            let self = this;
            let lead_type = self.initialState.getContext()['default_type'];
            this.$buttons.on('click', '.o_button_follow_up', function () {
                self.do_action({
                    name: 'Follow Up',
                    type: 'ir.actions.act_window',
                    res_model: 'crm.lead',
                    target: 'current',
                    views: [[self.crmFollowUpLeadTreeView, 'list']],
                    domain: [self.crmFollowUpLeadDomain],
                });
            });
            this.$buttons.on('click', '.o_button_generate_leads', function () {
                self.do_action({
                    name: 'Generate Leads',
                    type: 'ir.actions.act_window',
                    res_model: 'crm.iap.lead.mining.request',
                    target: 'new',
                    views: [[false, 'form']],
                    context: {'is_modal': true, 'default_lead_type': lead_type},
                });
            });
        }
    }

    let LeadFollowUpKanbanController = KanbanController.extend({
        willStart: function () {
            let self = this;
            let getFollowUpLeadData = self._rpc({
                model: 'crm.lead',
                method: 'get_follow_up_data',
                args: [],
            }).then(data => {
                [self.crmFollowUpLeadTreeView, self.crmFollowUpLeadDomain] = data;
            });
            let ready = this.getSession().user_has_group('sales_team.group_sale_salesman_all_leads')
                .then(function (is_sale_salesman) {
                    let buttons_template;
                    if (is_sale_salesman) {
                        buttons_template = 'LeadMiningRequestKanbanView.buttons';
                    } else {
                        buttons_template = 'AznutPortalKanbanView.buttons';
                    }
                    self.buttons_template = buttons_template;
                });
            return Promise.all([this._super.apply(this, arguments), ready, getFollowUpLeadData]);
        },
        renderButtons: function () {
            this._super.apply(this, arguments);
            renderFollowUpButton.apply(this, arguments);
        }
    });

    let LeadFollowUpKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: LeadFollowUpKanbanController,
        }),
    });
    viewRegistry.add('aznut_portal_follow_up_kanban', LeadFollowUpKanbanView);
});
