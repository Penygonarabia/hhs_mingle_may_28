odoo.define('your_module_name.FormViewDisableEdit', function (require) {
    "use strict";

    var FormView = require('web.FormView');
    var core = require('web.core');
    var rpc = require('web.rpc');

    FormView.include({
        load_record: function (record) {
            var self = this;
            return this._super(record).then(function () {
                if (self.modelName === 'hr.employee') {
                    rpc.query({
                        model: 'hr.employee',
                        method: 'read',
                        args: [[record.data.id], ['state']],
                    }).then(function (result) {
                        if (result && result[0].state === 'exit') {
                            console.log('Employee is in exit state, hiding edit button for record ID:', record.data.id);
                            self.$buttons.find('.o_form_button_edit').hide();
                        } else {
                            console.log('Employee state is not exit for record ID:', record.data.id);
                        }
                    });
                }
            });
        }
    });
});

