/** @odoo-module **/
import AbstractField from 'web.AbstractField';
import fieldRegistry from 'web.field_registry';
import { qweb } from "web.core";

const DeficitWidget = AbstractField.extend({
    template: "DeficitWidget",
    start: function(){
        this._super.apply(this, arguments);
        this.rpc = require('web.rpc');
        this.is_deficit = false;
    },
    _render: async function() {
        let production_start = false;
        const production_form = this.getParent().getParent();
        if (production_form){
            const is_production = production_form?.model === 'mrp.production',
                  prod_id = production_form?.res_id;
            if (is_production && prod_id){
                production_start = await this.rpc.query({
                    model: 'mrp.production',
                    method: 'is_production_started',
                    args: [[prod_id]]
                })
                if (production_start) {
                    this.is_deficit = false;
                }
            }
        }
        if (this.value && !production_start) {
            await this.rpc.query({
                model: 'stock.move',
                method: 'check_category',
                args: [[this.res_id]],
            }).then(function(data) {
                this.is_deficit = data ? true : false
            }.bind(this))
        }
        const render_context = {
            is_deficit: this.is_deficit,
        };
        this.$el.html(qweb.render(this.template, render_context));
    },
});

fieldRegistry.add('deficit_widget', DeficitWidget);
