/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { onMounted, onWillUpdateProps } from "@odoo/owl";

// Helper log (optional)
const log = (...args) => console.log("[promoter-check]", ...args);

let promoterIntervalId = null;
let promoterRedirectDone = sessionStorage.getItem("promoterRedirectDone") === "1";

patch(WebClient.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.user = useService("user");
        this.menu = useService("menu");

        const userId = session.uid;

        const toggleMenu = (menuXmlId, show) => {
            const menuEl = document.querySelector(`[data-menu-xmlid="${menuXmlId}"]`);
            if (!menuEl) return;

            // Hide both desktop and mobile <a> links
            const allLinks = menuEl.closest("li")?.querySelectorAll("a[data-menu-xmlid='" + menuXmlId + "']");
            if (allLinks) {
                allLinks.forEach(a => {
                    a.style.display = show ? "" : "none";
                });
            }

            // Hide any nested collapsible <div> and its <ul> children
            const nestedUl = menuEl.closest("li")?.querySelectorAll("ul");
            if (nestedUl) {
                nestedUl.forEach(ul => {
                    ul.style.display = show ? "" : "none";
                });
            }

            // Recursively hide child menus
            const childLis = menuEl.closest("li")?.querySelectorAll("ul li") || [];
            childLis.forEach(li => {
                const childLinks = li.querySelectorAll("a[data-menu-xmlid]");
                childLinks.forEach(aTag => toggleMenu(aTag.dataset.menuXmlid, show));
            });
        };

        const checkPromoterMenu = async () => {
            try {
                const inGroup = await this.user.hasGroup("promoter.group_promoter_user");
                if (!inGroup) {
                    if (promoterIntervalId) clearInterval(promoterIntervalId);
                    return;
                }

                const today = new Date().toISOString().slice(0, 10);
                const attendanceData = await this.orm.searchRead("hr.attendance", [
                    ["employee_id.user_id", "=", userId],
                    ["check_in", ">=", today + " 00:00:00"],
                    ["check_in", "<=", today + " 23:59:59"],
                ], ["check_in", "check_out"], { order: "check_in desc", limit: 1 });

                log("attendanceData:", attendanceData);

                const hasCheckIn = attendanceData.length > 0 && !!attendanceData[0].check_in;
                const hasCheckOut = attendanceData.length > 0 && !!attendanceData[0].check_out;
                const shouldHide = hasCheckIn && !hasCheckOut;

                // Toggle Promoter menu
                toggleMenu("promoter.menu_promoter_root", shouldHide);

                // 🟢 Reset redirect flag if user checked in again
                if (hasCheckIn && !hasCheckOut && promoterRedirectDone) {
                    log("New check-in detected -> reset redirect flag");
                    promoterRedirectDone = false;
                    sessionStorage.removeItem("promoterRedirectDone");
                }

                // 🔵 Redirect only once per checkout
                if (hasCheckOut && !promoterRedirectDone) {
                    log("Checkout detected -> performing one-time redirect");
                    promoterRedirectDone = true;
                    sessionStorage.setItem("promoterRedirectDone", "1");

                    if (promoterIntervalId) {
                        clearInterval(promoterIntervalId);
                        promoterIntervalId = null;
                        log("Interval cleared before redirect");
                    }

                    setTimeout(() => {
                        window.location.replace("/web");
                    }, 200);
                }

            } catch (err) {
                console.error("Error in checkPromoterMenu:", err);
            }
        };

        onMounted(() => checkPromoterMenu());
        onWillUpdateProps(() => checkPromoterMenu());

        promoterIntervalId = setInterval(checkPromoterMenu, 5000);
    },
});

