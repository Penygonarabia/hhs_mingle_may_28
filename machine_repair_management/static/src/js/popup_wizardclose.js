/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Composer } from "@mail/core/common/composer";

patch(Composer.prototype, {

    get CANCEL_OR_SAVE_EDIT_TEXT() {

        if (this.ui.isSmall) {

            // Return markup without the close button <button> and <i>

            return markup(

                sprintf(

                    escape(

                        _t(

                            "%(open_button)s%(open_em)sDiscard editing%(close_em)s%(close_button)s"

                        )

                    ),

                    {

                        open_button: `<button class='btn px-1 py-0' data-type="${escape(

                            EDIT_CLICK_TYPE.CANCEL

                        )}">`,

                        close_button: "",  // removed the close button closing tag or icon here

                        icon: "",  // removed icon

                        open_em: `<em data-type="${escape(EDIT_CLICK_TYPE.CANCEL)}">`,

                        close_em: "</em>",

                    }

                )

            );

        } else {

            // Remove the cancel <a> tag or whatever is responsible for close button

            const translation1 = _t(

                "%(open_samp)sEscape%(close_samp)s %(open_em)sto %(close_em)s, %(open_samp)sCTRL-Enter%(close_samp)s %(open_em)sto %(open_save)ssave%(close_save)s%(close_em)s"

            );

            const translation2 = _t(

                "%(open_samp)sEscape%(close_samp)s %(open_em)sto %(close_em)s, %(open_samp)sEnter%(close_samp)s %(open_em)sto %(open_save)ssave%(close_save)s%(close_em)s"

            );

            return markup(

                sprintf(escape(this.props.mode === "extended" ? translation1 : translation2), {

                    open_samp: "<samp>",

                    close_samp: "</samp>",

                    open_em: "<em>",

                    close_em: "</em>",

                    open_cancel: "",  // removed cancel anchor tag opening

                    close_cancel: "", // removed cancel anchor tag closing

                    open_save: `<a role="button" href="#" data-type="${escape(

                        EDIT_CLICK_TYPE.SAVE

                    )}">`,

                    close_save: "</a>",

                })

            );

        }

    },

});

