odoo.define('aznut_calculator_sign_quote.NameAndSignatureExtended', function (require) {
    "use strict";
    var registry = require('web.field_registry');
    var core = require('web.core');
    var signature = require('web.name_and_signature').NameAndSignature;
    signature.include({
        init: function () {
            arguments[1].fontColor = 'Black'
            this._super.apply(this, arguments);
        },
    })
})
