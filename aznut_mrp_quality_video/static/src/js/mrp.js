/** @odoo-module **/

import '@mrp/js/mrp';
import {MediaRecordDialog} from '../js/media_record_dialog/media_record_dialog';
import field_registry from 'web.field_registry';
import {bus} from 'web.core';

const {DateTime} = luxon;
const TimeCounter = field_registry.get('mrp_time_counter');
import time from 'web.time';
import fieldUtils from 'web.field_utils';

let GLOBAL_INTERVAL_ID = null;

window.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('redirectScheduled')) {
        localStorage.removeItem('redirectScheduled');
    }
    if (localStorage.getItem('_IS_RECORDING_DIALOG_OPEN')) {
        localStorage.removeItem('_IS_RECORDING_DIALOG_OPEN');
    }
})

TimeCounter.include({
    init: function () {
        this._super.apply(this, arguments);
        window._GLOBAL_DIALOG_TRIGER_TIMINGS = []
    },
    destroy: function () {
        this._super.apply(this, arguments);
        if (GLOBAL_INTERVAL_ID) {
            clearInterval(GLOBAL_INTERVAL_ID);
            GLOBAL_INTERVAL_ID = null;
        }
    },

    willStart: function () {
        var self = this;
        var def = this._rpc({
            model: 'mrp.workcenter.productivity',
            method: 'search_read',
            domain: [
                ['workorder_id', '=', this.record.data.id],
                ['date_end', '=', false],
            ],
        }).then(function (result) {
            var currentDate = new Date();
            var duration = 0;
            if (result.length > 0) {
                duration += self._getDateDifference(time.auto_str_to_date(result[0].date_start), currentDate);
            }
            var minutes = duration / 60 >> 0;
            var seconds = duration % 60;
            self.duration += minutes + seconds / 60;
    
            if (self.mode === 'edit') {
                self.value = self.duration;
            }
            if (self.viewType === 'form' && self.record?.data?.packaging_station) {
                let promise;
            
                if (!self.record.data.last_time_video_record || self.record.data.last_time_video_record === 0) {
                    promise = self._rpc({
                        model: 'mrp.workorder',
                        method: 'write',
                        args: [[self.record.data.id], {
                            last_time_video_record: self.record.data.duration,
                        }],
                    }).then(function () {
                        return self._rpc({
                            model: 'mrp.workorder',
                            method: 'read',
                            args: [[self.record.data.id], ['last_time_video_record']],
                        });
                    }).then(function (res) {
                        self.record.data.last_time_video_record = res[0].last_time_video_record;
                    });
                } else {
                    promise = Promise.resolve();
                }
                return promise.then(function () {
                    return self._rpc({
                        model: 'mrp.workorder',
                        method: 'get_quality_video_delay',
                        args: [[]]
                    });
                }).then(function (data) {
                    self.video_recording_delay = data;
                    return self._rpc({
                        model: 'mrp.workorder',
                        method: 'read',
                        args: [[self.record.data.id], ['can_record_video']],
                    });
                }).then(function (result) {
                    self.can_record_video = result[0].can_record_video
                });
            }
        });
        return Promise.all([this._super.apply(this, arguments), def]).then(function (){
            bus.on('open_video_dialog_manually', self, function (data) {
                if (!data || data.workorderId !== self.res_id || !self.viewType === 'form' || !self.record?.data?.packaging_station || !self.can_record_video) {
                    return;
                }
                if (!window.localStorage.getItem("_IS_RECORDING_DIALOG_OPEN")) {
                    self._triggerRecordingDialog(self.duration);
                }

            });
        });
        
    },

    _startTimeCounter: function () {
        var self = this;
        clearTimeout(this.timer);
        if (self.attrs.class && self.attrs.class.includes('aznut-counter') && self.duration > self.record.data.duration_expected) {
            self.$el.css('color', 'red')
        }
        if (self.viewType == 'form') {
            const utcTime = DateTime.utc();
            const gmtMinus4 = utcTime.setZone('UTC-4');
            const night_shift_user = self.recordData.night_shift_user;
            if (!(gmtMinus4.hour >= 5 && gmtMinus4.hour < 18) && !night_shift_user) {
                if (!window.localStorage.getItem("redirectScheduled")) {
                    window.localStorage.setItem("redirectScheduled", 'true')
                    self.displayNotification({
                        title: 'Notification',
                        type: 'danger',
                        sticky: true,
                        message: 'Workday is over! You will be redirected in 1 minute.'
                    });
                    setTimeout(() => {
                        window.location.href = '/web'
                    }, 60000);
                }
            }
        }
        if (this.record.data.is_user_working) {
            this.timer = setTimeout(function () {
                self.duration += 1 / 60;

                if (self.viewType === 'form' && self.record?.data?.packaging_station && self.can_record_video) {
                    const is_dialog_open = window.localStorage.getItem("_IS_RECORDING_DIALOG_OPEN");
                    const delay = parseFloat(self.video_recording_delay || 0) * 60,
                          lastRecorded = parseFloat(self.record.data.last_time_video_record || 0),
                          current = parseFloat(self.duration || 0);
                    if (!is_dialog_open && current - lastRecorded >= delay) {
                        self._triggerRecordingDialog(current);
                    }
                }
                self._startTimeCounter();
            }, 1000);
        } else {
            clearTimeout(this.timer);
        }
    
        this.$el.text(fieldUtils.format.float_time(this.duration));
    },
    _triggerRecordingDialog: function () {
        var self = this;
        window.localStorage.setItem("_IS_RECORDING_DIALOG_OPEN", 'true')
        self.recording_dialog = self._renderVideoDialog();
        self.recording_dialog.open();
    },
    _renderVideoDialog: function () {
        return new MediaRecordDialog(this,{
            body: 'test',
            title: 'Metal Detector Check',
            mo_name: this.record.data.display_name,
            mo_id: this.record.data.production_id.res_id,
            wo_id: this.record.res_id,
            clearTimer: async () => {
                window.localStorage.setItem("_IS_RECORDING_DIALOG_OPEN", '')
                const current = parseFloat(this.duration || 0);
                this.record.data.last_time_video_record = current;
                await this._rpc({
                    model: 'mrp.workorder',
                    method: 'write',
                    args: [[this.record.data.id], {
                        last_time_video_record: current,
                    }],
                });
            }
        });
    },
})
