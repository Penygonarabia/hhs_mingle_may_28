/** @odoo-module **/
import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import RestrictStockPopup from "@pos_restrict_product_stock/js/RestrictStockPopup";

patch(Order.prototype, {
    async pay() {
        try {
            const type = this.pos.config.stock_type;
            if (!this.pos.config.is_restrict_product) {
                return super.pay();
            }

            // Get POS location from picking type
            const posLocationId = this.pos.config.picking_type_id?.default_location_src_id?.id;
            if (!posLocationId) {
                console.error("POS location not configured properly");
                return super.pay();
            }

            const outOfStockProducts = [];
            for (const line of this.orderlines) {
                const productContext = line.product.with_context({'location': posLocationId});
                const posQtyAvailable = productContext.qty_available || 0;
                const posVirtualAvailable = productContext.virtual_available || 0;

                if ((type === 'qty_on_hand' && posQtyAvailable <= 0) ||
                    (type === 'virtual_qty' && posVirtualAvailable <= 0)) {
                    outOfStockProducts.push(line.product.display_name);
                }
            }

            if (outOfStockProducts.length > 0) {
                const confirmed = await this.pos.popup.add(RestrictStockPopup, {
                    body: outOfStockProducts.join(', ')
                });
                if (confirmed) {
                    return super.pay();
                }
                return;
            }

            return super.pay();
        } catch (error) {
            console.error("Error in pay:", error);
            return super.pay();
        }
    }
});