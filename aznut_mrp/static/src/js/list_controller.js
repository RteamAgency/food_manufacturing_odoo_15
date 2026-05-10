odoo.define('tree_view_button.tree_view_header_buttons', function (require) {
    "use strict";

    const ListController = require('web.ListController');
    const viewUtils = require('web.viewUtils');

    ListController.include({
        _VisibleHeaderButtons() {
            const buttonClasses = 'btn-primary btn-secondary btn-link btn-success btn-info btn-warning btn-danger'.split(' ');
            let $buttonsContainer = $();
            const buttonsToRemove = [];

            this.headerButtons.forEach(buttonNode => {
                if (!buttonNode.attrs.modifiers?.header_visible_button) {
                    return;
                }

                const $button = viewUtils.renderButtonFromNode(buttonNode);
                $button.addClass('btn');

                if (!buttonClasses.some(cls => $button.hasClass(cls))) {
                    $button.addClass('btn-secondary');
                }

                $button.on("click", this._onHeaderButtonClicked.bind(this, buttonNode));
                $buttonsContainer = $buttonsContainer.add($button);
                buttonsToRemove.push(buttonNode);
            });

            $buttonsContainer.appendTo(this.$buttons);
            this.headerButtons = this.headerButtons.filter(button => !buttonsToRemove.includes(button));
        },

        renderButtons($node) {
            this._super.apply(this, arguments);
            this._VisibleHeaderButtons();
        },
    });
});
