/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import RestrictStockPopup from "@pos_restrict_product_stock/js/RestrictStockPopup";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async addProductToCurrentOrder(...args) {
        try {
            const product = args[0];
            const type = this.config?.stock_type;

            // Validate configuration and product
            if (!this.config || !product) {
                console.warn("POS configuration or product is undefined.");
                return await super.addProductToCurrentOrder(...args);
            }

            // Fetch POS location ID safely
            const pickingType = this.config.picking_type_id;
             console.log("POS picking Type",pickingType);
            const posLocationId = pickingType?.default_location_src_id;
            console.log("POs Localtion ID",posLocationId)

            if (!posLocationId) {
                console.warn("No valid POS location configured. Skipping stock restriction.");
                return await super.addProductToCurrentOrder(...args);
            }

            if (this.config.is_restrict_product) {
                // Get quantities in POS location
                const productContext = product.with_context({ location: posLocationId });
                const posQtyAvailable = productContext.qty_available || 0;
                const posVirtualAvailable = productContext.virtual_available || 0;

                // Compare against location-specific quantities
                if (
                    (type === 'qty_on_hand' && posQtyAvailable <= 0) ||
                    (type === 'virtual_qty' && posVirtualAvailable <= 0)
                ) {
                    await this.popup.add(RestrictStockPopup, {
                        body: `Product "${product.display_name}" is out of stock in the current location.`,
                        pro_id: product.id,
                    });
                    return;
                }
            }

            // Proceed to add the product to the order
            await super.addProductToCurrentOrder(...args);
        } catch (error) {
            console.error("Error in addProductToCurrentOrder:", error);
            return await super.addProductToCurrentOrder(...args);
        }
    },
});
