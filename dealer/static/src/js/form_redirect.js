// import { registry } from "@web/core/registry";
// import FormController from "@web/views/form/form_controller";

// class RedirectFormController extends FormController {
//     async saveRecord(...args) {
//         const res = await super.saveRecord(...args);
//         console.log("[RedirectFormController] saveRecord called, result:", res);

//         if (res && !this.env.isAutosave) {
//             try {
//                 const user = this.env.services.user;

//                 const isMobileUser = await user.hasGroup("promoter.group_promoter_user");
//                 const isBackofficeUser = await user.hasGroup("promoter.group_promoter_backoffice_user");

//                 console.log("[RedirectFormController] Groups:", { isMobileUser, isBackofficeUser });

//                 if (isMobileUser) {
//                     console.log("[RedirectFormController] Redirecting → Mobile action");
//                     await this.actionService.doAction("promoter.action_promoter_sales_mobile");
//                 } else if (isBackofficeUser) {
//                     console.log("[RedirectFormController] Redirecting → Backoffice action");
//                     await this.actionService.doAction("promoter.action_promoter_showroom_sales");
//                 } else {
//                     console.log("[RedirectFormController] Redirect fallback → Backoffice action");
//                     await this.actionService.doAction("promoter.action_promoter_showroom_sales");
//                 }
//             } catch (err) {
//                 console.error("[RedirectFormController] redirect failed", err);
//             }
//         }

//         return res;
//     }
// }

// const formView = registry.category("views").get("form");
// registry.category("views").add("promoter_sales_redirect_form", {
//     ...formView,
//     Controller: RedirectFormController,
// });
