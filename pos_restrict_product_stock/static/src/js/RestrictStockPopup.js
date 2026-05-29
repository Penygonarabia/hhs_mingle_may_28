/** @odoo-module **/
import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";

class RestrictStockPopup extends AbstractAwaitablePopup {
    static template = 'RestrictStockPopup';

    setup() {
        super.setup();
        this.title = _t("Out of Stock");
        this.body = this.props.body;
    }

    async _OrderProduct() {
        try {
            if(this.props.pro_id) {
                const product = this.env.pos.db.get_product_by_id(this.props.pro_id);
                if (product) {
                    this.env.pos.get_order().add_product(product);
                }
            }
            this.props.resolve(true);
            this.cancel();
        } catch (error) {
            console.error("Popup Error:", error);
            this.props.resolve(false);
        }
    }
}

export default RestrictStockPopup;