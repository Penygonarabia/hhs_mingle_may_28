/** 
 * promoter/static/src/js/get_gps.js
 * ES module style for saving user GPS
 */

import { FormController } from "@web/views/form/form_controller";
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";

const GPSFormController = FormController.extend({

    async _onSave(...args) {
        try {
            const position = await this._getCurrentPosition();

            // Save coordinates to res.users for the current logged-in user
            await rpc({
                model: "res.users",
                method: "write",
                args: [[this.env.session.uid], {
                    current_latitude: position.coords.latitude,
                    current_longitude: position.coords.longitude,
                }],
            });

        } catch (err) {
            console.warn("Could not get location:", err);
            this.displayNotification({
                title: "Location Error",
                message: "Could not get your location. Please enable GPS.",
                type: "warning",
            });
        }

        // Call the original _onSave for the form
        return super._onSave(...args);
    },

    _getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(resolve, reject);
            } else {
                reject(new Error("Geolocation not supported"));
            }
        });
    },

});

// Register the extended controller
registry.category("controllers").add("promoter.gps_form_controller", GPSFormController);
