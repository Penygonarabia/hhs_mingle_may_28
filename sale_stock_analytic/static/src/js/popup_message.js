odoo.define('sale_stock_analytic.popup_message', function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');
    var Dialog = require('web.Dialog');

    var QWeb = core.qweb;
    var _t = core._t;

    var PopupMessage = Widget.extend({
        template: 'sale_stock_analytic.popup_message_template',

        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.message = options.message || _t("A required field is not filled out.");
        },

        start: function () {
            var self = this;
            this.dialog = new Dialog(this, {
                size: 'medium',
                title: _t("Popup Message"),
                buttons: [{
                    text: _t("Close"),
                    classes: 'btn-secondary',
                    click: function () {
                        self.dialog.close();
                    },
                }],
            });
            this.dialog.open();
            return this._super.apply(this, arguments);
        },
    });
    
    

    core.action_registry.add('popup_message', PopupMessage);

    return PopupMessage;
});


$('action_post').click(function () {
    var PopupMessage = require('sale_stock_analytic.popup_message');
    var popup = new PopupMessage(this, {
        message: "The required field 'Analytic Account' is not filled out.",
    });
    popup.appendTo($('body'));
});
