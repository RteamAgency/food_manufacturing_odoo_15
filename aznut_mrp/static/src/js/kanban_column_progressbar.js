odoo.define('aznut_mrp.KanbanColumnProgressBar', function (require) {
    'use strict';

    const KanbanColumnProgressBar = require('web.KanbanColumnProgressBar');
    const {patch} = require('web.utils');
    var utils = require('web.utils');
    const core = require('web.core');
    const _t = core._t;


    patch(KanbanColumnProgressBar.prototype, 'aznut_mrp.KanbanColumnProgressBar', {
        _render: function () {
            var self = this;
            this.trigger_up('tweak_column', {
                callback: function ($el) {
                    $el.removeClass('o_kanban_group_show');
                    _.each(self.colors, function (val, key) {
                        $el.removeClass('o_kanban_group_show_' + val);
                    });
                    if (self.activeFilter.value) {
                        $el.addClass('o_kanban_group_show o_kanban_group_show_' + self.colors[self.activeFilter.value]);
                    }
                },
            });
            this.trigger_up('tweak_column_records', {
                callback: function ($el, recordData) {
                    var categoryValue = recordData[self.fieldName] ? recordData[self.fieldName] : '__false';
                    _.each(self.colors, function (val, key) {
                        $el.removeClass('oe_kanban_card_' + val);
                    });
                    if (self.colors[categoryValue]) {
                        $el.addClass('oe_kanban_card_' + self.colors[categoryValue]);
                    }
                },
            });

            var barNumber = 0;
            var barMinWidth = 6; // In %
            const selection = self.columnState.fields[self.fieldName].selection;
            _.each(self.colors, function (val, key) {
                var $bar = self.$bars[key];
                var count = self.subgroupCounts && self.subgroupCounts[key] || 0;

                if (!$bar) {
                    return;
                }

                // Adapt tooltip
                let value;
                if (selection) { // progressbar on a field of type selection
                    const option = selection.find(option => option[0] === key);
                    value = option && option[1] || _t('Other');
                } else {
                    value = key;
                }
                $bar.attr('data-original-title', count + ' ' + value);
                $bar.tooltip({
                    delay: 0,
                    trigger: 'hover',
                });

                $bar.toggleClass('progress-bar-animated progress-bar-striped', key === self.activeFilter.value);

                $bar.removeClass('o_bar_has_records transition-off');
                window.getComputedStyle($bar[0]).getPropertyValue('width'); // Force reflow so that animations work
                if (count > 0) {
                    $bar.addClass('o_bar_has_records');
                    // Make sure every bar that has records has some space
                    // and that everything adds up to 100%
                    var maxWidth = 100 - barMinWidth * barNumber;
                    self.$('.progress-bar.o_bar_has_records').css('max-width', maxWidth + '%');
                    $bar.css('width', (count * 100 / self.groupCount) + '%');
                    barNumber++;
                    $bar.attr('aria-valuemin', 0);
                    $bar.attr('aria-valuemax', self.groupCount);
                    $bar.attr('aria-valuenow', count);
                } else {
                    $bar.css('width', '');
                }
            });
            this.$('.progress-bar').css('min-width', '');
            this.$('.progress-bar.o_bar_has_records').css('min-width', barMinWidth + '%');

            var start = this.prevTotalCounterValue;
            var end = this.totalCounterValue;

            if (this.activeFilter.value) {
                if (this.sumField) {
                    end = 0;
                    _.each(self.columnState.data, function (record) {
                        var recordData = record.data;
                        if (self.activeFilter.value === recordData[self.fieldName] ||
                            (self.activeFilter.value === '__false' && !recordData[self.fieldName])) {
                            end += parseFloat(recordData[self.sumField]);
                        }
                    });
                } else {
                    end = this.subgroupCounts[this.activeFilter.value];
                }
            }
            const applyChanges = this.columnState.model === 'mrp.production' && this.columnState.viewType === 'kanban';
            let productQty, totalBatchesCount;
            if (applyChanges) {
                productQty = this.columnState.aggregateValues?.product_qty;
                totalBatchesCount = this.columnState.data.reduce((sum, item) => {
                    return sum + (item.data?.batches_count || 0);
                }, 0);
            }

            this.prevTotalCounterValue = end;
            var animationClass = start > 999 ? 'o_kanban_grow' : 'o_kanban_grow_huge';

            if (start !== undefined && (end > start || this.activeFilter.value) && this.ANIMATE) {
                $({currentValue: start}).animate({currentValue: end}, {
                    duration: 1000,
                    start: function () {
                        self.$counter.addClass(animationClass);
                    },
                    step: function () {
                        self.$number.html(_getCounterHTML(this.currentValue));
                        if (applyChanges) {
                            self.$number.html(`${totalBatchesCount} / ${productQty || 0}`);
                        }
                    },
                    complete: function () {
                        self.$number.html(_getCounterHTML(this.currentValue));
                        if (applyChanges) {
                            self.$number.html(`${totalBatchesCount} / ${productQty || 0}`);
                        }
                        self.$counter.removeClass(animationClass);
                    },
                });
            } else {
                this.$number.html(_getCounterHTML(end));
                if (applyChanges) {
                    self.$number.html(`${totalBatchesCount} / ${productQty || 0}`);
                }
            }

            function _getCounterHTML(value) {
                return utils.human_number(value, 0, 3);
            }
        },
    });
});
