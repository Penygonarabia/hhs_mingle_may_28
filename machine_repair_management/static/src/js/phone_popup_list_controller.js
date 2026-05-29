/** @odoo-module **/
 
import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
 
export class PhonePopupListController extends ListController {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.UpdateRecord = this.UpdateRecord.bind(this);
    }
 
    async UpdateRecord() {
        const selectedRecords = this.model.root.selection;
 
        if (selectedRecords.length !== 1) {
            this.notification.add("⚠️ Please select exactly one task.", {
                className: "bg-warning",
            });
            return;
        }
 
        const selectedRecord = selectedRecords[0];
        const recordData = selectedRecord.data;
 
        console.log("✅ Selected record:", selectedRecord);
        console.log("📦 Record data:", recordData);
 
        const product_category_id = recordData?.product_category_id?.[0] || false;
        const product_category_display_name = recordData?.product_category_id?.[1] || "";
        const product_id = recordData?.product_id?.[0] || false;
        const product_display_name = recordData?.product_id?.[1] || "";
 
        const purchase_invoice_no = recordData?.purchase_invoice_no || "";
        const purchase_date = recordData?.purchase_date || "";
	
   
        const dealer_id = recordData?.dealer_id?.[0] || false;
		const dealer_display_name = recordData?.dealer_id?.[1] || "";

		
        const warranty = recordData?.warranty; // ensure boolean
        const warranty_expiry_Date = recordData?.warranty_expiry_Date || ""; // raw date object or string
 	
		const building_number = recordData?.building_number || "";
		
		const plot_identification = recordData?.plot_identification || "";
		
		const svc_id = recordData?.svc_id?.[0] || false;
		const svc_display_name = recordData?.svc_id?.[1] || "";

		const product_slno = recordData?.product_slno || "";
		
		const product_group_id = recordData?.product_group_id?.[0] || false;
		let product_group_id_display_name = recordData?.product_group_id?.[1] || false;
		
		const product_sub_group_id = recordData?.product_sub_group_id?.[0] || false;
		let product_sub_group_id_display_name = recordData?.product_sub_group_id?.[1] || false;
		
		const service_warranty_id = recordData?.service_warranty_id?.[0] || false;
		
		/*const service_warranty_display_name = recordData?.service_warranty_id?.[1] || "";*/
		
		let service_warranty_display_name = recordData?.service_warranty_id?.[1] || "";

		if (service_warranty_id && !service_warranty_display_name) {
		    // Fetch via name_get
		    const result = await this.rpc("/web/dataset/call_kw", {
		        model: "service.warranty", // replace with your actual model
		        method: "name_get",
		        args: [[service_warranty_id]],
				kwargs: {}, 
		    });
		    service_warranty_display_name = result[0][1];
		}
		
		if (product_group_id && !product_group_id_display_name){
			
			const result = await this.rpc("/web/dataset/call_kw",{
				
				model : "product.category",
				method: "name_get",
				args:[[product_group_id]],
				kwargs:{},
				
				
			});
			product_group_id_display_name = result[0][1];
			
		}
		
		if (product_sub_group_id && !product_sub_group_id_display_name){
			
			const result = await this.rpc("/web/dataset/call_kw",{
				
				model : "product.category",
				method : "name_get",
				args :[[product_sub_group_id]],
				kwargs:{},
				
			});
			product_sub_group_id_display_name = result[0][1];
		}
		
        const payload = {
            type: "update_support_fields",
            product_category_id,
            product_category_display_name,
            product_id,
            product_display_name,
            purchase_invoice_no,
            purchase_date,
            dealer_id,
			dealer_display_name,
            warranty,
            warranty_expiry_Date,
			building_number,
			plot_identification,
			svc_id,
			product_slno,
			product_group_id,
			product_group_id_display_name,
			product_sub_group_id,
			product_sub_group_id_display_name,
			close_popup: true,
			service_warranty_id,
			service_warranty_display_name,
			
			
        };
 
        console.log("📤 Sending to parent:", payload);
 
        // Send the message to parent window
        window.parent.postMessage(payload, "*");
 
        /*this.notification.add("✅ Product details sent to parent form.", {
            className: "bg-success",
        });*/
    }
}
 
registry.category("views").add("phone_popup_list_view", {
    ...registry.category("views").get("list"),
    Controller: PhonePopupListController,
});