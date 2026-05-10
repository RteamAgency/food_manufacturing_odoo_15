/** @odoo-module */
import Dialog from "web.Dialog";
import core from "web.core";
import session from 'web.session';

const OwlDialog = require('web.OwlDialog');

var QWeb = core.qweb;
var _t = core._t;


export const MediaRecordDialog = Dialog.extend({

    // -----------------------------
    // Initialization and Setup
    // -----------------------------
    template: 'aznut_mrp_quality_video.MediaRecordDialog',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/aznut_mrp_quality_video/static/src/xml/media_record_dialog/media_record_dialog.xml']
    ),
    init: function (parent, options, error) {
        this._super.apply(this, [parent, options]);
        this.available_devices = [];
        this.permissionsGranted = true;
        this.is_device_selected = false;
        this.buttons = [];
        this.mo_name = options.mo_name;
        this.mo_id = options.mo_id;
        this.wo_id = options.wo_id;
        this.is_check_failed = false;
        this._boundOnChangeRecordingState = this._onChangeRecordingState.bind(this);
        this._boundOnSendVideo = this._onSendVideo.bind(this);
        this._boundOnClickFailButton = this._onClickFailButton.bind(this);
        this._boundOnChangeCameraSelection = this._onChangeCameraSelection.bind(this);
        this.clearTimer = options.clearTimer;
    },

    willStart: function () {
        var self = this;
    
        var checkCameraPermissions = navigator.mediaDevices.getUserMedia({ video: true })
        .then(function (stream) {
            self.permissionsGranted = true;
            stream.getTracks().forEach(track => track.stop());
        })
        .catch(function () {
            self.permissionsGranted = false;
        });
    
        var superPromise = this._super.apply(this, arguments);
    
        return Promise.all([checkCameraPermissions, superPromise]).then(function () {
            self.renderModal()
            return self.initSelectCamera()
                .then(function () {
                    return self.startVideo();
                })
        });
    },

    open: function (options) {
        $('.tooltip').remove();
        var self = this;
        this.appendTo($('<div/>')).then(function () {
            if (self.isDestroyed()) {
                return;
            }
            self.$modal.attr('open', true);
            if (self.$parentNode) {
                self.$modal.appendTo(self.$parentNode);
            }
            self.$modal.modal({
                show: true,
                backdrop: self.backdrop,
                keyboard: false,
            });
            self.$modal.on('keydown.dismiss.bs.modal', function (e) {
                if (e.which === 27) {
                    e.stopPropagation();
                    e.preventDefault();
                }
            });
            self._openedResolver();
            if (options && options.shouldFocusButtons) {
                self._onFocusControlButton();
            }
            OwlDialog.display(self);

            core.bus.trigger("legacy_dialog_opened", self);
        });

        return self;
    },

    destroy: function () {
        this._super.apply(this, arguments);
        if (this._recordingTimeout) {
            clearTimeout(this._recordingTimeout);
            this._recordingTimeout = null;
        }
        this.recording_control?.removeEventListener('change', this._boundOnChangeRecordingState);
        this.passButton?.removeEventListener('click', this._boundOnSendVideo);
        this.failButton?.removeEventListener('click', this._boundOnClickFailButton);
        this.selectCamera?.removeEventListener('change', this._boundOnChangeCameraSelection);
        if (this.clearTimer && !this._is_destroyed) {
            this.clearTimer();
        }
        this._is_destroyed = true;
    },

    // -----------------------------
    // Rendering and UI setup
    // -----------------------------

    renderModal: function () {
        this.$modal = $(QWeb.render('aznut_mrp_quality_video.MediaRecordDialog', {
            fullscreen: this.fullscreen,
            title: this.title,
            subtitle: this.subtitle,
            technical: this.technical,
            renderHeader: this.renderHeader,
            renderFooter: this.renderFooter,
            permissionsGranted: this.permissionsGranted,
            devices_available: this.available_devices.length,
            is_device_selected: this.id_device_selected,
        }));
        switch (this.size) {
            case 'extra-large':
                this.$modal.find('.modal-dialog').addClass('modal-xl');
                break;
            case 'large':
                this.$modal.find('.modal-dialog').addClass('modal-lg');
                break;
            case 'small':
                this.$modal.find('.modal-dialog').addClass('modal-sm');
                break;
        }

        if (this.renderFooter) {
            this.$footer = this.$modal.find(".modal-footer");
            this.set_buttons(this.buttons);
        }

        this.$modal.on('hidden.bs.modal', _.bind(this.destroy, this));

        this.selectCamera = this.$modal[0].querySelector('#selectCamera');
        this.video = this.$modal[0].querySelector('#quality_video');
        this.recording_control = this.$modal[0].querySelector('#start_stop_recording');
        this.passButton = this.$modal[0].querySelector('#pass_btn');
        this.failButton = this.$modal[0].querySelector('#fail_btn');
        this.preview_tab = this.$modal[0].querySelector('#preview_pill');
        this.recording_pill = this.$modal[0].querySelector('a[href="#pills_recording"]');
        this.currentSnapshot = this.$modal[0].querySelector('#current_snapshot');

        this.recording_control.addEventListener('change', this._boundOnChangeRecordingState);
        this.passButton.addEventListener('click', this._boundOnSendVideo);
        this.failButton.addEventListener('click', this._boundOnClickFailButton);
    },

    renderVideoBlock: function() {
        this.$modal.find("#video_block").replaceWith(QWeb.render('aznut_mrp_quality_video.VideoBlock', {
            permissionsGranted: this.permissionsGranted,
            is_device_selected: this.is_device_selected,
        }));

        this.video = this.$modal[0].querySelector('#quality_video');
        this.currentSnapshot = this.$modal[0].querySelector('#current_snapshot');
    },

    // -----------------------------
    // Camera & Video Logic
    // -----------------------------

    async initSelectCamera() {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(device => device.kind === 'videoinput');
        videoDevices.map(videoDevice => {
            if (!this.available_devices.includes(videoDevice.deviceId)){
                let opt = document.createElement('option');
                opt.value = videoDevice.deviceId;
                opt.innerHTML = videoDevice.label;
                this.available_devices.push(videoDevice.deviceId);
                this.selectCamera.appendChild(opt);
                this.selectCamera.addEventListener('change', this._boundOnChangeCameraSelection);
                return opt;
            }
        })
    },

    async startVideo(device = null) {
        if (device) {
            try {
                const videoStream = await this.getVideoConfig(device);
                await this.handleStream(videoStream)
            } catch (e) {
                this.alertPermissionsError();
            }
        }
    },

    stopVideo() {
        this.streamStarted = false;
        if (this.video && this.video.srcObject)
            this.video.srcObject.getTracks().forEach((track) => {
                track.stop();
        });
    },

    async handleStream(stream) {
        const def = $.Deferred();

        if (stream && stream.getVideoTracks().length)
            this.selectCamera.value = stream.getVideoTracks()[0].getSettings().deviceId;
        this.video.srcObject = stream;

        this.video.addEventListener("canplay", () => {
            this.video.play();
        });

        this.video.addEventListener("loadedmetadata", () => {
            this.streamStarted = true;
            def.resolve();
        }, false);

        return def
    },

    async getVideoConfig(device) {
        let config = {
            video: {
                width: { ideal: session.am_webcam_width || 1280 },
                height: { ideal: session.am_webcam_height || 720 },
            },
            audio: true,
        };
        if (device)
            config.video.deviceId = { exact: device };
    
        const videoStream = await navigator.mediaDevices.getUserMedia(config);
        return videoStream;
    },

    // -----------------------------
    // Recording and Upload
    // -----------------------------

    _onChangeRecordingState: function (ev) {
        if (!this.is_check_failed) {
            if (ev.target.checked) {
                this._onStartRecording();
            } else {
                if (this._recordingTimeout) {
                    clearTimeout(this._recordingTimeout);
                    this._recordingTimeout = null;
                }
                this._onStopRecording();
            }
        } else {
            this._onClickTakeSnapshot();
        }

    },

    _onStartRecording: async function () {
        const max_duration = await this._rpc({
            model: 'mrp.workorder',
            method: 'get_quality_video_max_duration',
            args: [[]]
        })
        const raw = parseFloat(max_duration);
        const totalSeconds = raw * 60;
        const durationMs = Math.round(totalSeconds * 1000);
        if (!this.video.srcObject) return;
    
        this.recordedChunks = [];
        try {
            this.recorder = RecordRTC(this.video.srcObject, {
                type: 'video',
                mimeType: 'video/webm;codecs=vp8,opus',
                disableLogs: true,
                timeSlice: 1000,
                ondataavailable: (blob) => {
                    this.recordedChunks.push(blob);
                }
            });
    
            this.recorder.startRecording();

            this._recordingTimeout = setTimeout(() => {
                this.recording_control.click()
            }, durationMs);
    
        } catch (err) {
            console.error('RecordRTC init error:', err);
            this.alertPermissionsError();
        }
    },

    _onStopRecording: function () {
        return new Promise((resolve) => {
            if (!this.recorder) {
                resolve(null);
                return;
            }
    
            this.recorder.stopRecording(() => {
                const blob = this.recorder.getBlob();
                this.videoBlob = blob;
                this.preview_tab.classList.remove('disabled');
    
                const videoURL = URL.createObjectURL(blob);
    
                const reviewVideo = document.createElement('video');
                reviewVideo.src = videoURL;
                reviewVideo.controls = true;
                reviewVideo.width = 640;
                reviewVideo.height = 480;
    
                const container = this.$modal.find('#videoReviewContainer')[0];
                container.innerHTML = '';
                container.appendChild(reviewVideo);

                reviewVideo.onloadedmetadata = () => {
                    reviewVideo.currentTime = 0;
                    resolve(blob);
                };
            });
        });
    },

    _onSendVideo: async function() {
        if (!this.videoBlob) {
            return;
        }
        const fileName = this.generateVideoName();
        const formData = new FormData();
        formData.append('video', this.videoBlob, fileName);
        formData.append('mo_id', this.mo_id);
        fetch('/packaging/send_quality_video', {
            method: 'POST',
            body: formData,
        }).then(response => {
            if (response.ok) {
                this.call('notification', 'notify', {
                    message: 'Video successfully uploaded!',
                    type: 'success'
                })
                $.unblockUI();
                this.destroy()
            } else {
                this.call('notification', 'notify', {
                    message: 'Error when sending a video.',
                    type: 'danger'
                })
                $.unblockUI();
            }
        });
    },


    _onChangeCameraSelection: async function(ev) {
        const device = $(ev.target).val(),
              record_button_wrap = this.recording_control.closest('.record_btn_wrap')
        if (device) {
            if (record_button_wrap) {
                record_button_wrap.classList.remove('invisible');
            }
            this.is_device_selected = true;
            this.renderVideoBlock()
            await this.stopVideo()
            await this.startVideo(device)
        } else{ 
            if (record_button_wrap) {
                record_button_wrap.classList.add('invisible');
            }
            this.is_device_selected = false;
            this.renderVideoBlock()
        }
    },
    
    // -----------------------------
    // Fail scenario: Snapshot + Alert
    // -----------------------------

    _onClickFailButton: async function() {
        this.recording_pill.click();
        this.preview_tab.classList.add('disabled');
        this.is_check_failed = true;
        this.recording_control.closest('.record_btn').classList.add('no-record');
    },

    _onClickTakeSnapshot() {
        const fail_btns = document.querySelector('.fail_buttons');
        this.selectCamera.disabled = true;
        this.video.classList.add('d-none');
        this.currentSnapshot.classList.remove('d-none');
        this.currentSnapshot.src = this.takeSnap(this.video);
        if (fail_btns) {
            const save_btn = fail_btns.querySelector("#save_btn"),
                  retake_btn = fail_btns.querySelector("#retake_btn");

            save_btn.addEventListener('click', this._onCreateQualityAlert.bind(this))
            retake_btn.addEventListener('click', this._onClickRetakeButton.bind(this))
            fail_btns.classList.remove('fail_buttons-hidden');
        }

        this.recording_control.closest('.record_btn_wrap').classList.add('d-none');
        
    },

    _onClickRetakeButton: function(ev) {
        const fail_btns = document.querySelector('.fail_buttons');
        fail_btns.classList.add('fail_buttons-hidden');
        this.selectCamera.disabled = false;
        this.currentSnapshot.classList.add('d-none');
        this.currentSnapshot.src = '';
        this.video.classList.remove('d-none');
        this.recording_control.closest('.record_btn_wrap').classList.remove('d-none');
    },

    takeSnap: function(video) {
        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const canvasContext = canvas.getContext("2d");
        canvasContext.drawImage(video, 0, 0);
        return canvas.toDataURL('image/jpeg');
    },

    _onCreateQualityAlert: async function() {
        this.displayLoading();
        await this._rpc({
            model: 'mrp.workorder',
            method: 'create_quality_video_alert',
            args: [[this.wo_id], this.currentSnapshot.src],
        })
        $.unblockUI();
        this.destroy();
    },

    // -----------------------------
    // Utility Methods
    // -----------------------------

    generateVideoName: function() {
        const now = new Date(), 
              dateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`,
              timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`,
              timezoneOffset = -now.getTimezoneOffset(),
              sign = timezoneOffset >= 0 ? "+" : "-",
              tzHours = String(Math.floor(Math.abs(timezoneOffset) / 60)).padStart(2, '0'),
              tzMinutes = String(Math.abs(timezoneOffset) % 60).padStart(2, '0'),
              timezoneStr = `GMT${sign}${tzHours}:${tzMinutes}`;

        return `${this.mo_name} - ${dateStr} - ${timeStr} (${timezoneStr}).webm`
    },

    alertPermissionsError: function(){
        Dialog.alert(
            this,
            _t(`Unable to access the video camera. 
                Please ensure that you have granted the necessary permissions
                to use your camera in your browser settings.`),
            {
                title: _t('Access Denied')
            }
        );
    },
    displayLoading: function () {
        var msg = _t("We are processing your video, please wait ...");
        $.blockUI({
            'message': '<h2 class="text-white"><img src="/web/static/img/spin.png" class="fa-pulse"/>' +
                '    <br />' + msg +
                '</h2>'
        });
    },
});
