/** @odoo-module **/


import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useEffect } from "@odoo/owl";
import { debounce } from "@web/core/utils/timing";

const { DateTime } = luxon;

export class PhonePopupController extends FormController {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.lastCheckedPhone = null; // Track the last checked phone number

        this.checkPhoneNumber = debounce(this.checkPhoneNumber.bind(this), 500);
        // console.log("📲 PhonePopupController setup initialized");
		
		const toOdooDate = (raw) => {
            if (!raw) return false;

            // Already a valid Luxon DateTime?
            if (raw && raw.isValid && typeof raw.toFormat === "function") {
                return raw;
            }

            let dateStr = null;

            if (typeof raw === "string") {
                dateStr = raw.trim();
            }
            else if (raw?.c?.year !== undefined) {
                const { year, month, day } = raw.c;
                dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            }
            else if (raw?.year && raw?.month && raw?.day) {
                dateStr = `${raw.year}-${String(raw.month).padStart(2, '0')}-${String(raw.day).padStart(2, '0')}`;
            }
            else if (raw instanceof Date && !isNaN(raw)) {
                dateStr = raw.toISOString().split('T')[0];
            }

            if (dateStr && /^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
                const dt = DateTime.fromISO(dateStr);
                return dt.isValid ? dt : false;
            }

            console.warn("Invalid date format:", raw);
            return false;
        };

        useEffect(() => {
            const phone = this.model.root.data.phone;
            // Only trigger check in create mode, if phone exists and is different from the last checked phone
            if (this.model.root.isNew && phone && phone !== this.lastCheckedPhone) {
                console.log("📞 Phone changed to:", phone);
                this.checkPhoneNumber(phone);
                this.lastCheckedPhone = phone; // Update the last checked phone
            }
        }, () => [this.model.root.data.phone]);

        window.addEventListener("message", async (event) => {
            const data = event.data;

            if (data.type === "update_support_fields") {
                console.log("📩 Received support field data:", data);

             


                const requiredFields = [
                    "product_category",
                    "product_id",
                    "purchase_invoice_no",
                    "purchase_date",
                    "dealer_id",
                    "warranty",
                    "website_year",
					"building_number",
					"plot_identification",
					"svc_id",
					"product_slno",
					"product_group_id",
					"product_sub_group_id",
					"sr_service_warranty_id",
				
					
					
					
                ];

                for (const field of requiredFields) {
                    if (!this.model.root.fields[field]) {
                        console.error(`❌ Field missing in form view: ${field}`);
                        /*this.notification.add(`⚠️ Missing field in form: ${field}`, {
                            className: "bg-warning",
                        });*/
                        return;
                    }
					
                }
				
			
				
                const updatesStep1 = {
                    product_category: data.product_category_id
                        ? [data.product_category_id, data.product_category_display_name || ""]
                        : false,
                    purchase_invoice_no: data.purchase_invoice_no || "",
 
					purchase_date: toOdooDate(data.purchase_date),

					dealer_id: data.dealer_id?[data.dealer_id,data.dealer_display_name || ""]
								:false,
                    warranty: !!data.warranty,
					
                   	website_year: toOdooDate(data.warranty_expiry_Date),
					building_number : data.building_number || "",
					plot_identification : data.plot_identification || "",
					svc_id : data.svc_id ? [data.svc_id,data.svc_display_name || ""] : false,
					product_slno : data.product_slno || "",
					product_group_id: data.product_group_id
					                       ? [data.product_group_id, data.product_group_id_display_name || ""]
					                       : false,
				   product_sub_group_id: data.product_sub_group_id
				                          ? [data.product_sub_group_id, data.product_sub_group_id_display_name || ""]
				                          : false,		
										  
										  			   
					sr_service_warranty_id: data.service_warranty_id 
							?[data.service_warranty_id,data.service_warranty_display_name || ""]
							: false,
							
                };

                const updatesStep2 = {
                    product_id: data.product_id
                        ? [data.product_id, data.product_display_name || ""]
                        : false,
                };

                try {
                    console.log("🛠️ Updating Step 1 fields:", updatesStep1);
                    await this.model.root.update(updatesStep1);

                    console.log("🛠️ Updating product_id:", updatesStep2);
                    await this.model.root.update(updatesStep2);

                    console.log("✅ All fields updated.");
                    /*this.notification.add("✅ Product and warranty fields updated successfully.", {
                        className: "bg-success",
                    });*/
					if (data.close_popup) {
			            console.log("🧹 Asking Odoo to close popup via actionService...");
			            this.actionService.doAction({ type: "ir.actions.act_window_close" });
			        }
                } catch (error) {
                    console.error("❌ Error updating fields:", error);
                    /*this.notification.add("❌ Failed to update fields. See console for details.", {
                        className: "bg-danger",
                    });*/
                }
            }
        });
    }

    async checkPhoneNumber(phone) {
        try {
            const normalizedPhone = phone.replace(/[\s\-+()]/g, '');
            console.log("🔍 Checking phone:", normalizedPhone);

            const result = await this.rpc("/machine_repair/phone_popup", {
                params: {
                    phone: normalizedPhone,
                },
            });

            console.log("🔍 RPC Result:", result);
            if (result) {
                console.log("✅ Task matched. Opening popup window.");
                this.actionService.doAction(result);
            } else {
                console.log("❌ No customer found in this mobile number:", normalizedPhone);
               /* this.notification.add("❌ No matching task found for phone.", {
                    type: "warning",
                });*/
            }
        } catch (error) {
            console.error("🚨 RPC Error:", error);
            this.notification.add("❌ Failed to check phone number.", {
                type: "error",
            });
        }
    }
}

registry.category("views").add("phone_popup_hook", {
    ...registry.category("views").get("form"),
    Controller: PhonePopupController,
});
 

/*import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useEffect } from "@odoo/owl";
import { debounce } from "@web/core/utils/timing";
 
export class PhonePopupController extends FormController {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.actionService = useService("action");
        this.notification = useService("notification"); // Initialize notification service
 	
        this.checkPhoneNumber = debounce(this.checkPhoneNumber.bind(this), 500);
        console.log("📲 PhonePopupController setup initialized");
 
        useEffect(() => {
            const phone = this.model.root.data.phone;
            if (phone) {
                console.log("📞 Phone changed to:", phone);
                this.checkPhoneNumber(phone);
            }
        }, () => [this.model.root.data.phone]);
 
 
        window.addEventListener("message", async (event) => {
            const data = event.data;
 
            if (data.type === "update_support_fields") {
                console.log("📩 Received support field data:", data);
 
                // ✅ Convert Luxon DateTime to 'DD-MM-YYYY'
                const toDateString = (dt) => {
                    if (dt && typeof dt.toFormat === "function") {
                        return dt.toFormat("dd-MM-yyyy");
                    }
                    return null;
                };
 
                // ✅ Required fields that must exist in the form
                const requiredFields = [
                    "product_category",
                    "product_id",
                    "purchase_invoice_no",
                    "purchase_date",
                    "purchase_dealer_name",
                    "warranty",
                    "website_year",  // corresponds to warranty_expiry_Date
                ];
 
                for (const field of requiredFields) {
                    if (!this.model.root.fields[field]) {
                        console.error(`❌ Field missing in form view: ${field}`);
                        this.notification.add(`⚠️ Missing field in form: ${field}`, {
                            className: "bg-warning",
                        });
                        return;
                    }
                }
 
                // ✅ Prepare update values
                const updatesStep1 = {
                    product_category: data.product_category_id
                        ? [data.product_category_id, data.product_category_display_name || ""]
                        : false,
                    purchase_invoice_no: data.purchase_invoice_no || "",
                    purchase_date: toDateString(data.purchase_date), // format: DD-MM-YYYY
                    purchase_dealer_name: data.purchase_dealer_name || "",
                    warranty: !!data.warranty,
                    website_year: toDateString(data.warranty_expiry_Date), // format: DD-MM-YYYY
                };
 
                const updatesStep2 = {
                    product_id: data.product_id
                        ? [data.product_id, data.product_display_name || ""]
                        : false,
                };
 
                try {
                    console.log("🛠️ Updating Step 1 fields:", updatesStep1);
                    await this.model.root.update(updatesStep1);
 
                    console.log("🛠️ Updating product_id:", updatesStep2);
                    await this.model.root.update(updatesStep2);
 
                    console.log("✅ All fields updated.");
                    this.notification.add("✅ Product and warranty fields updated successfully.", {
                        className: "bg-success",
                    });
                } catch (error) {
                    console.error("❌ Error updating fields:", error);
                    this.notification.add("❌ Failed to update fields. See console for details.", {
                        className: "bg-danger",
                    });
                }
            }
        });
 
    }
 
    async checkPhoneNumber(phone) {
        try {
            const normalizedPhone = phone.replace(/[\s\-+()]/g, '');
//            const uniqueCode = this.model.root.data.unique_code;
 
            if (!uniqueCode) {
                console.warn("⚠️ Unique code is empty or not yet generated.");
                this.notification.add("⚠️ Unique code is empty or not yet generated.", {
                    type: "warning",
                });
                return;
            }
 
            console.log("🔍 Checking phone:", normalizedPhone);
//            console.log("🆔 With unique_code:", uniqueCode);
 
            const result = await this.rpc("/machine_repair/phone_popup", {
                params: {
                    phone: normalizedPhone,
//                    unique_code: uniqueCode,
                },
            });
 
            console.log("🔍 RPC Result:", result);
            if (result) {
                console.log("✅ Task matched. Opening popup window.");
                this.actionService.doAction(result);
            } else {
                console.log("❌ No matching task found for phone:", normalizedPhone);
                this.notification.add("❌ No matching task found for phone.", {
                    type: "warning",
                });
            }
        } catch (error) {
            console.error("🚨 RPC Error:", error);
            this.notification.add("❌ Failed to check phone number.", {
                type: "error",
            });
        }
    }
}
 
registry.category("views").add("phone_popup_hook", {
    ...registry.category("views").get("form"),
    Controller: PhonePopupController,
});
 */


/*import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useEffect } from "@odoo/owl";
import { debounce } from "@web/core/utils/timing";
 
export class PhonePopupController extends FormController {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.actionService = useService("action");
        this.checkPhoneNumber = debounce(this.checkPhoneNumber.bind(this), 500);
 
        console.log("PhonePopupController setup hook fired");
 
        useEffect(() => {
            const phone = this.model.root.data.phone;
            if (phone) {
                console.log("Phone changed:", phone);
                this.checkPhoneNumber(phone);
            }
        }, () => [this.model.root.data.phone]);
    }
 
    async checkPhoneNumber(phone) {
        try {
            const normalizedPhone = phone.replace(/[\s\-+()]/g, '');
            console.log("RPC Call with phone:", normalizedPhone);
            const result = await this.rpc("/machine_repair/phone_popup", {
                params: { phone: normalizedPhone },
            });
            if (result) {
                console.log("Matched project.task, opening:", result);
                this.actionService.doAction(result);
            } else {
                console.log("No matching task found for phone:", normalizedPhone);
            }
        } catch (error) {
            console.error("RPC Error:", error);
        }
    }
}
 
registry.category("views").add("phone_popup_hook", {
    ...registry.category("views").get("form"),
    Controller: PhonePopupController,
});*/
 