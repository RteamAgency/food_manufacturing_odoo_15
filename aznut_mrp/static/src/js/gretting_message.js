odoo.define('aznut_mrp.greeting_message', function (require) {
    "use strict";

    const {patch} = require('web.utils');
    const core = require('web.core');
    const _t = core._t;
    const GreetingMessage = require('hr_attendance.greeting_message');

    patch(GreetingMessage.prototype, 'aznut_mrp.GreetingMessage', {
        welcome_message: function () {
            let self = this;
            let now = this.attendance.check_in.clone();
            this.return_to_main_menu = setTimeout(function () {
                self.do_action(self.next_action, {clear_breadcrumbs: true});
            }, 10000);
            this._rpc({
                model: 'mrp.workorder',
                method: 'find_workorders_by_employee',
                args: [this.attendance.employee_id[0]],
            }).then(function (response) {
                if (response) {
                    let insertPoint = $('h2.o_hr_attendance_message_message');
                    let newElement = $('<div>', {class: 'mb-4'});
                    let h2 = $('<h2>', {text: 'You are assigned to:', style: 'font-size:22px;'});
                    newElement.append(h2)
                    response.forEach(function (item) {
                        let header = $('<p>', {
                            class: 'mt-2 mb-0 text-center fs-1',
                            style: 'font-size:20px;color: #F08080;'
                        });
                        let bold = $('<b>', {
                            text: item.header,
                        })
                        header.append(bold)


                        newElement.append(header);
                    });
                    insertPoint.after(newElement);
                }
            });


            if (now.hours() < 5) {
                this.$('.o_hr_attendance_message_message').append(_t("Good night"));
            } else if (now.hours() < 12) {
                if (now.hours() < 8 && Math.random() < 0.3) {
                    if (Math.random() < 0.75) {
                        this.$('.o_hr_attendance_message_message').append(_t("The early bird catches the worm"));
                    } else {
                        this.$('.o_hr_attendance_message_message').append(_t("First come, first served"));
                    }
                } else {
                    this.$('.o_hr_attendance_message_message').append(_t("Good morning"));
                }
            } else if (now.hours() < 17) {
                this.$('.o_hr_attendance_message_message').append(_t("Good afternoon"));
            } else if (now.hours() < 23) {
                this.$('.o_hr_attendance_message_message').append(_t("Good evening"));
            } else {
                this.$('.o_hr_attendance_message_message').append(_t("Good night"));
            }
            if (this.previous_attendance_change_date) {
                let last_check_out_date = this.previous_attendance_change_date.clone();
                if (now - last_check_out_date > 24 * 7 * 60 * 60 * 1000) {
                    this.$('.o_hr_attendance_random_message').html(_t("Glad to have you back, it's been a while!"));
                } else {
                    if (Math.random() < 0.02) {
                        this.$('.o_hr_attendance_random_message').html(_t("If a job is worth doing, it is worth doing well!"));
                    }
                }
            }
        },
    });
});
