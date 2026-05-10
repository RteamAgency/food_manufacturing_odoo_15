/** @odoo-module **/


import {ProjectListView} from '@project/js/project_list';
import {_t} from 'web.core';
import Dialog from 'web.Dialog';


ProjectListView.prototype.config.Controller.include({
    async _stopRecurrence(recurringResIds, resIds, mode) {
        const recurrenceIdsSet = new Set();
        for (const record of this.getSelectedRecords()) {
            const recurrenceId = record.data.recurrence_id;
            if (recurrenceId) {
                recurrenceIdsSet.add(recurrenceId);
            }
        }
        const recurrenceIds = Array.from(recurrenceIdsSet);
        let countsLeft = await this._countRecordsPerReccurence(recurrenceIds, recurringResIds);
        countsLeft = countsLeft.map(rec => rec.recurrence_id[0]);
        const allowContinue = recurrenceIds.every(rec => countsLeft.includes(rec));

        let warning;
        if (resIds.length > 1) {
            warning = allowContinue
                ? _t('It seems that some tasks are part of a recurrence.')
                : _t('It seems that some tasks are part of a recurrence. At least one of them must be kept as a model to create the next occurences.');
        } else {
            warning = allowContinue
                ? _t('It seems that this task is part of a recurrence.')
                : _t('It seems that this task is part of a recurrence. You must keep it as a model to create the next occurences.');
        }

        const dialog = new Dialog(this, {
            buttons: [
                {
                    classes: 'btn-primary',
                    click: () => {
                        this._rpc({
                            model: 'project.task',
                            method: 'action_stop_recurrence',
                            args: [recurringResIds],
                        }).then(() => {
                            if (mode === 'archive') {
                                this._toggleArchiveState(true);
                            } else if (mode === 'delete') {
                                this._deleteRecords(resIds);
                            }
                        });
                    },
                    close: true,
                    text: _t('Stop Recurrence'),
                },
                {
                    close: true,
                    text: _t('Discard'),
                }
            ],
            size: 'medium',
            title: _t('Confirmation'),
            $content: $('<main/>', {
                role: 'alert',
                text: warning,
            }),
        });

        if (allowContinue) {
            dialog.buttons.splice(1, 0,
                {
                    click: () => {
                        this._rpc({
                            model: 'project.task',
                            method: 'action_continue_recurrence',
                            args: [recurringResIds],
                        }).then(() => {
                            if (mode === 'archive') {
                                this._toggleArchiveState(true);
                            } else if (mode === 'delete') {
                                this._deleteRecords(resIds);
                            }
                        });
                    },
                    close: true,
                    text: _t('Continue Recurrence'),
                });
        }

        dialog.open();
    }
});


