/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";

console.log("Promoter GEO validation loaded");

class PromoterSalesListController extends ListController {
    async _onCreate(ev) {
        console.log("Create button clicked!");

        const user = this.env.session.user_context;
        console.log("User context:", user);

        if (!user || !user.has_group_promoter_user) {
            console.log("Not a promoter, fallback");
            return super._onCreate(ev);
        }

        try {
            // Fetch promoter coordinates
            const userCoords = await this._rpc({
                model: "res.users",
                method: "read",
                args: [[this.env.session.uid], ["current_latitude", "current_longitude"]],
            });
            const userLat = userCoords[0].current_latitude;
            const userLon = userCoords[0].current_longitude;
            console.log("User coords RPC:", userLat, userLon);

            if (!userLat || !userLon) {
                console.warn("Missing user location!");
                await this._showWarning("Location Missing", "Please enable GPS to create sales.");
                return;
            }

            // Fetch assignment
            const assignment = await this._rpc({
                model: "promoter.assignment",
                method: "search_read",
                args: [[["promoter_id", "=", this.env.session.uid]], ["showroom_id"]],
                limit: 1,
            });
            console.log("Assignment RPC:", assignment);

            if (!assignment.length || !assignment[0].showroom_id) {
                console.warn("No showroom assigned!");
                await this._showWarning("Showroom Missing", "No showroom assigned for you.");
                return;
            }

            const showroomId = assignment[0].showroom_id[0];

            // Fetch showroom coordinates
            const showroomData = await this._rpc({
                model: "promoter.showroom",
                method: "read",
                args: [[showroomId], ["latitude", "longitude"]],
            });
            const showroomLat = showroomData[0].latitude;
            const showroomLon = showroomData[0].longitude;
            console.log("Showroom data RPC:", showroomLat, showroomLon);

            if (!showroomLat || !showroomLon) {
                console.warn("Showroom coordinates missing!");
                await this._showWarning("Showroom Location Missing", "Cannot create new sales.");
                return;
            }

            // Compute Haversine distance
            const R = 6371000; // meters
            const toRad = (x) => (x * Math.PI) / 180;
            const dLat = toRad(showroomLat - userLat);
            const dLon = toRad(showroomLon - userLon);
            const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(userLat)) * Math.cos(toRad(showroomLat)) * Math.sin(dLon / 2) ** 2;
            const distance = 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
            console.log("Distance to showroom:", distance);

            const allowedDistance = 100;

            if (distance > allowedDistance) {
                console.warn("Out of range!");
                await this._showWarning("Out of Range", `You are ${Math.round(distance)} meters away.`);
                return;
            }

            console.log("Validation passed");
            return super._onCreate(ev);

        } catch (err) {
            console.error("GEO validation error:", err);
            return super._onCreate(ev);
        }
    }

    async _showWarning(title, message) {
        console.log("Dialog:", title, message);
        await this.env.services.dialog.add(this, {
            title,
            body: message,
            buttons: [{ text: "Ok", close: true }],
        });
    }
}

// Proper registration in Odoo 17
registry.category("view_controllers").add("promoter_showroom_sales_list_controller", {
    type: "list",
    model: "promoter.showroom.sales",
    controller: PromoterSalesListController,
    force: true,
});