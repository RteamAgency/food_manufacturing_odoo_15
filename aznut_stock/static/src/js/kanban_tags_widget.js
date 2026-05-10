/** @odoo-module **/
import AbstractField from 'web.AbstractField';
import fieldRegistry from 'web.field_registry';
import { qweb } from "web.core";


const StockKanbanTags = AbstractField.extend({
    template: "StockSourceTags",
    start: function(){
        const val = this.recordData['stock_source_tags']
        this.value = [];
        if (!val || val === "false"){
            this.value = [];
        }
        else {
            const tags = JSON.parse(val);
            this.value = tags;
        }
        this._super.apply(this, arguments);
    },
    _render: function() {
        const values = this.value ? this.value : [];
        const isListView = (this.viewType === 'list') ? true : false; 
        const render_context = {
            field_values: values,
            isListView: isListView,
        };
        this.$el.html(qweb.render(this.template, render_context));
    },
});

fieldRegistry.add('stock_source_tags', StockKanbanTags);
