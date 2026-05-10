odoo.define('aznut_portal.website_sale', function (require) {
    'use strict';

    let publicWidget = require('web.public.widget');
    require('website_sale.website_sale');

    publicWidget.registry.WebsiteSale.include({
        events: _.extend({}, publicWidget.registry.WebsiteSale.prototype.events, {
            'change input.js_batch_quantity': '_onChangeAddBatchesQuantity',
            'click button.js_add_batches_cart_json': '_onClickAddBatchesQuantityButtons',
        }),

        _onClickAddBatchesQuantityButtons: function (ev) {
            let $link = $(ev.currentTarget),
                $input = $('input[id="batches_count"]'),
                min = parseFloat($input.data("min") || 0),
                max = parseFloat($input.data("max") || Infinity),
                previousQty = parseFloat($input.val() || 0, 10),
                quantity = ($link.has(".fa-minus").length ? -1 : 1) + previousQty,
                newQty;
            newQty = quantity > min ? (quantity < max ? quantity : max) : min;
            if (newQty !== previousQty) {
                $input.val(newQty).trigger('change');
            }
            return false;
        },
        _onChangeAddBatchesQuantity: function (ev) {
            let batchesSpan = document.querySelector("span[data-batches-count]"),
                batch = batchesSpan?.dataset.batchesCount,
                $link = $(ev.currentTarget),
                $input = $('input[name="add_qty"]'),
                min = parseFloat($input.data("min") || 0),
                max = parseFloat($input.data("max") || Infinity),
                previousQty = parseFloat($input.val() || 0, 10),
                quantity,
                newQty;
            if (batch) {
                quantity = $link.val() * batch;
            } else {
                quantity = previousQty;
            }
            newQty = quantity > min ? (quantity < max ? quantity : max) : min;
            if (newQty !== previousQty) {
                $input.val(newQty).trigger('change');
            }
            return false;
        },
        _onChangeAddQuantity: function (ev) {
            let inputQty = document.querySelector('input[name="add_qty"]'),
                batchesSpan = document.querySelector("span[data-batches-count]"),
                batch = batchesSpan?.dataset.batchesCount,
                batchesInput = document.getElementById('batches_count'),
                batchesCount;
            if (inputQty && batch >= 1 && inputQty.value % batch === 0) {
                batchesCount = inputQty.value / batch;
            } else {
                batchesCount = 0;
            }
            if (batchesInput){
                batchesInput.value = batchesCount;
            }
            this._super(...arguments)
        },
        _onClickAdd: async function (ev) {
            let batchesSpan = document.querySelector("span[data-batches-count]"),
                $input = $('input[id="batches_count"]'),
                batch = batchesSpan?.dataset.batchesCount;
            if ($input.length && parseFloat($input.val()) === 0 && batch) {
                this.call('notification', 'notify', {
                    message: `Need to provide a quantity that is divisible by ${batch}!`,
                    type: 'danger'
                })
            } else {
                return await this._super.apply(this, arguments)
            }
        }
    });
    return publicWidget.registry.WebsiteSaleQuantityInherit;
});