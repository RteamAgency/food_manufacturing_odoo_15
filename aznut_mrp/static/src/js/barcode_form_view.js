odoo.define('aznut_mrp.FormView', function (require) {
    "use strict";

    var BarcodeEvents = require('barcodes.BarcodeEvents'); // handle to trigger barcode on bus
    var core = require('web.core');
    var FormController = require('web.FormController');

    var _t = core._t;
    var rpc = require('web.rpc');
    const Dialog = require('web.Dialog');


    FormController.include({
        async _barcodeScanned(barcode, target) {
            var self = this;
            const model = self.initialState.context.active_model || self.initialState.model,
                active_id = self.initialState.context.active_id || self.initialState.res_id;
            if (self.initialState.context.aznut_mrp) {
                await rpc.query({
                    model: model,
                    method: 'validate_package_lines',
                    args: [[active_id], {'barcode': barcode}],
                }).catch(function (error) {
                    error.event.preventDefault();
                    var error_body = _t('Something went wrong!');
                    if (error.message.data) {
                        var except = error.message.data;
                        error_body = except.arguments && except.arguments[0];
                    }
                    Dialog.alert(self, _t(error_body));
                });
                self.update({}, {reload: true});
                return
            }
            return this.barcodeMutex.exec(function () {
                var prefixed = _.any(BarcodeEvents.ReservedBarcodePrefixes,
                    function (reserved) {
                        return barcode.indexOf(reserved) === 0;
                    });
                var hasCommand = false;
                var defs = [];
                if (!$.contains(target, self.el)) {
                    return;
                }
                for (var k in self.activeBarcode) {
                    var activeBarcode = self.activeBarcode[k];
                    var methods = self.activeBarcode[k].commands;
                    var method = prefixed ? methods[barcode] : methods.barcode;
                    if (method) {
                        if (prefixed) {
                            hasCommand = true;
                        }
                        defs.push(self._barcodeActiveScanned(method, barcode, activeBarcode));
                    }
                }
                if (prefixed && !hasCommand) {
                    self.displayNotification({
                        title: _t('Undefined barcode command'),
                        message: barcode,
                        type: 'danger'
                    });
                }
                return self.alive(Promise.all(defs)).then(function () {
                    if (!prefixed) {
                        self.current_barcode = barcode;
                        self.update({}, {reload: false});
                    }
                });
            });
        },
    })
})