/** @odoo-module **/
import { localization } from "@web/core/l10n/localization";
import { session } from "@web/session";

function checkAndApplyRTL() {
    try {
        const lang = (session.user_context && session.user_context.lang) || 
                     document.documentElement.getAttribute("lang") || 
                     "";
        const isArabic = lang.startsWith("ar") || localization.direction === "rtl";
        if (isArabic) {
            if (document.documentElement.getAttribute("dir") !== "rtl") {
                document.documentElement.setAttribute("dir", "rtl");
                document.documentElement.setAttribute("lang", "ar");
            }
            if (!document.body.classList.contains("o_rtl")) {
                document.body.classList.add("o_rtl");
                document.body.setAttribute("dir", "rtl");
            }
        }
    } catch (e) {
        // silent fail
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", checkAndApplyRTL);
} else {
    checkAndApplyRTL();
}

// Watch for SPA transitions
setInterval(checkAndApplyRTL, 1000);
