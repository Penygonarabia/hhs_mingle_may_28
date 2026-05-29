/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";

export const UserLocationService = {
    dependencies: ["notification", "orm"],

    async start(env) {
        this.notification = env.services.notification;
        this.orm = env.services.orm;

        const captureLocation = async () => {
            if (!session.uid) {
                console.warn("No logged in user. Skipping location capture.");
                /*this.notification.add("Please log in to capture your location.", { type: "warning" });*/
                return;
            }

            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    async (position) => {
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        console.log("User location:", lat, lon);

                        try {
                            // ✅ Call your Python method
                            await this.orm.call(
                                "res.users",
                                "update_current_location",
                                [],   // no positional args
                                { latitude: lat, longitude: lon } // kwargs
                            );

                            console.log("Location saved successfully");
                            /*this.notification.add("Your location has been saved.", { type: "success" });*/
                        } catch (err) {
                            console.error("Failed to save location:", err);
                            /*this.notification.add("Failed to save location.", { type: "danger" });*/
                        }
                    },
                    (error) => {
                        console.warn("Geolocation failed:", error.message);
                        /*this.notification.add("Unable to retrieve your location: " + error.message, {
                            type: "warning",
                        });*/
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0,
                    }
                );
            } else {
                console.warn("Geolocation not supported");
                /*this.notification.add("Geolocation is not supported by your browser.", { type: "warning" });*/
            }
        };

        // Run automatically after session is initialized
        if (session.uid) {
            console.log("session.uid",session.uid)
            captureLocation();
        } else {
            let attempts = 0;
            const maxAttempts = 10;
            const interval = setInterval(() => {
                if (session.uid) {
                    clearInterval(interval);
                    captureLocation();
                } else if (attempts >= maxAttempts) {
                    clearInterval(interval);
                    console.warn("Could not detect login session.");
                    /*this.notification.add("Unable to detect user login.", { type: "warning" });*/
                }
                attempts++;
            }, 1000);
        }
    },
};

// Register service
registry.category("services").add("user_location", UserLocationService);


///** @odoo-module **/
//
//import { registry } from "@web/core/registry";
//import { session } from "@web/session";
//
//export const UserLocationService = {
//    start(env) {
//        const orm = env.services.orm;
//        const notification = env.services.notification;
//
//        async function captureLocation() {
//            if (!session.uid) {
//                console.warn("No logged in user. Skipping location capture.");
//                notification.add("Please log in to capture your location.");
//                return;
//            }
//
//            if (navigator.geolocation) {
//                navigator.geolocation.getCurrentPosition(
//                    async (position) => {
//                        const lat = position.coords.latitude;
//                        const lon = position.coords.longitude;
//                        console.log("User location:", lat, lon);
//
//                        try {
//                            // ✅ Use orm.write to update the user directly
//                            await orm.write("res.users", [session.uid], {
//                                current_latitude: lat,
//                                current_longitude: lon,
//                            });
//
//                            console.log("Location saved successfully");
//                            notification.add("Your location has been saved.");
//                        } catch (err) {
//                            console.error("Failed to save location:", err);
//                            notification.add("Failed to save location.");
//                        }
//                    },
//                    (error) => {
//                        console.warn("Geolocation failed:", error.message);
//                        notification.add("Unable to retrieve your location: " + error.message);
//                    },
//                    {
//                        enableHighAccuracy: true,
//                        timeout: 10000,
//                        maximumAge: 0,
//                    }
//                );
//            } else {
//                console.warn("Geolocation not supported");
//                notification.add("Geolocation is not supported by your browser.");
//            }
//        }
//
//        if (session.uid) {
//            captureLocation();
//        }
//    },
//};
//
//registry.category("services").add("user_location", UserLocationService);


///** @odoo-module **/
//
//import { registry } from "@web/core/registry";
//import { useService } from "@web/core/utils/hooks";
//import { session } from "@web/session";
//
//export const UserLocationService = {
//    // Must use start(env) for services
//    start(env) {
//        // Access Odoo services
//        const notification = env.services.notification;
//        const rpc = env.services.rpc;
//
//        async function captureLocation() {
//            if (!session.uid) {
//                console.warn("No logged in user. Skipping location capture.");
//                notification.add("Please log in to capture your location.");
//                return;
//            }
//
//            if (navigator.geolocation) {
//                navigator.geolocation.getCurrentPosition(
//                    async (position) => {
//                        const lat = position.coords.latitude;
//                        const lon = position.coords.longitude;
//                        console.log("User location:", lat, lon);
//
//                        try {
//                            await this.rpc("/web/dataset/call_kw", {
//                                model: "res.users",
//                                method: "update_current_location",
//                                args: [lat, lon],
//                                kwargs: {},
//                            });
//
//                            console.log("Location saved successfully");
//                            notification.add("Your location has been saved.");
//                        } catch (err) {
//                            console.error("Failed to save location:", err);
//                            notification.add("Failed to save location.");
//                        }
//                    },
//                    (error) => {
//                        console.warn("Geolocation failed:", error.message);
//                        notification.add("Unable to retrieve your location: " + error.message);
//                    },
//                    {
//                        enableHighAccuracy: true,
//                        timeout: 10000,
//                        maximumAge: 0,
//                    }
//                );
//            } else {
//                console.warn("Geolocation not supported");
//                notification.add("Geolocation is not supported by your browser.");
//            }
//        }
//
//        // Automatically run after session is ready
//        if (session.uid) {
//            captureLocation();
//        } else {
//            // Wait for session initialization
//            let attempts = 0;
//            const maxAttempts = 10;
//            const interval = setInterval(() => {
//                if (session.uid) {
//                    clearInterval(interval);
//                    captureLocation();
//                } else if (attempts >= maxAttempts) {
//                    clearInterval(interval);
//                    console.warn("Could not detect login session.");
//                    notification.add("Unable to detect user login.");
//                }
//                attempts++;
//            }, 1000);
//        }
//    },
//};
//
//// Register the service
//registry.category("services").add("user_location", UserLocationService);


///** @odoo-module **/
//
//import { registry } from "@web/core/registry";
//import { session } from "@web/session";
//
//export const UserLocationService = {
//    start(env) {
//        const notification = env.services.notification;
//
//        async function captureLocation() {
//            if (!session.uid) {
//                console.warn("No logged in user. Skipping location capture.");
//                notification.add("Please log in to capture your location.");
//                return;
//            }
//
//            if (navigator.geolocation) {
//                navigator.geolocation.getCurrentPosition(
//                    async (position) => {
//                        const lat = position.coords.latitude;
//                        const lon = position.coords.longitude;
//                        console.log("User location:", lat, lon);
//
//                        try {
//                            await rpc({
//                                model: "res.users",
//                                method: "update_current_location",
//                                args: [[session.uid], lat, lon],
//                                kwargs: {},
//                            });
//                            console.log("Location saved successfully");
//                            notification.add("Your location has been saved.");
//                        } catch (err) {
//                            console.error("Failed to save location:", err);
//                            notification.add("Failed to save location.");
//                        }
//                    },
//                    (error) => {
//                        console.warn("Geolocation failed:", error.message);
//                        notification.add("Unable to retrieve your location: " + error.message);
//                    },
//                    {
//                        enableHighAccuracy: true,
//                        timeout: 10000,
//                        maximumAge: 0,
//                    }
//                );
//            } else {
//                console.warn("Geolocation not supported");
//                notification.add("Geolocation is not supported by your browser.");
//            }
//        }
//
//        // Run automatically after session is initialized
//        if (session.uid) {
//            captureLocation();
//        } else {
//            let attempts = 0;
//            const maxAttempts = 10;
//            const interval = setInterval(() => {
//                if (session.uid) {
//                    clearInterval(interval);
//                    captureLocation();
//                } else if (attempts >= maxAttempts) {
//                    clearInterval(interval);
//                    console.warn("Could not detect login session.");
//                    notification.add("Unable to detect user login.");
//                }
//                attempts++;
//            }, 1000);
//        }
//    },
//};
//
//// Register service
//registry.category("services").add("user_location", UserLocationService);


///** @odoo-module **/
//
//import { registry } from "@web/core/registry";
//import { session } from "@web/session";
////import rpc from "web.rpc";
//import { rpc } from "@web/core/network/rpc"; // 🔹 Correct import
//
//
//export const UserLocationService = {
//    start(env) {
//        const notification = env.services.notification;
//        const rpc = env.services.rpc;
//
//        async function captureLocation() {
//            if (!session.uid) {
//                console.warn("No logged in user. Skipping location capture.");
//                notification.add("Please log in to capture your location.");
//                return;
//            }
//
//            if (navigator.geolocation) {
//                navigator.geolocation.getCurrentPosition(
//                    async (position) => {
//                        const lat = position.coords.latitude;
//                        const lon = position.coords.longitude;
//                        console.log("User location:", lat, lon);
//
//                        try {
//                            await rpc.query({
//                                model: "res.users",
//                                method: "update_current_location",
//                                args: [[session.uid], lat, lon],
//                                kwargs: {},
//                            });
//                            console.log("Location saved successfully");
//                            notification.add("Your location has been saved.");
//                        } catch (err) {
//                            console.error("Failed to save location:", err);
//                            notification.add("Failed to save location.");
//                        }
//                    },
//                    (error) => {
//                        console.warn("Geolocation failed:", error.message);
//                        notification.add("Unable to retrieve your location: " + error.message);
//                    },
//                    {
//                        enableHighAccuracy: true,
//                        timeout: 10000,
//                        maximumAge: 0,
//                    }
//                );
//            } else {
//                console.warn("Geolocation not supported");
//                notification.add("Geolocation is not supported by your browser.");
//            }
//        }
//
//        // Run automatically after session is initialized
//        if (session.uid) {
//            captureLocation();
//        } else {
//            let attempts = 0;
//            const maxAttempts = 10;
//            const interval = setInterval(() => {
//                if (session.uid) {
//                    clearInterval(interval);
//                    captureLocation();
//                } else if (attempts >= maxAttempts) {
//                    clearInterval(interval);
//                    console.warn("Could not detect login session.");
//                    notification.add("Unable to detect user login.");
//                }
//                attempts++;
//            }, 1000);
//        }
//    },
//};
//
//// Register service
//registry.category("services").add("user_location", UserLocationService);



///** @odoo-module **/
//
//import { registry } from "@web/core/registry";
//import { session } from "@web/session";
//
//export const UserLocationService = {
//    start(env) {
//        const rpc = env.services.rpc;
//        const notification = env.services.notification;
//
//        async function captureLocation() {
//            if (!session.uid) {
//                console.warn("No logged in user. Skipping location capture.");
//                notification.add("Please log in to capture your location.", { type: "warning" });
//                return;
//            }
//
//            if (navigator.geolocation) {
//                navigator.geolocation.getCurrentPosition(
//                    async (position) => {
//                        const lat = position.coords.latitude;
//                        const lon = position.coords.longitude;
//                        console.log("User location:", lat, lon);
//
//                        try {
////                            await rpc({
////                                model: "res.users",
////                                method: "update_current_location",
////                                args: [lat, lon],
////                                kwargs: {},
////                            });
//                            await rpc.query({
//                                model: "res.users",
//                                method: "update_current_location",
//                                args: [[session.uid], lat, lon],
//                                kwargs: {},
//                            });
//                            console.log("Location saved successfully");
//                            notification.add("Your location has been saved.", { type: "success" });
//                        } catch (err) {
//                            console.error("Failed to save location:", err);
//                            notification.add("Failed to save location.", { type: "error" });
//                        }
//                    },
//                    (error) => {
//                        console.warn("Geolocation failed:", error.message);
//                        notification.add("Unable to retrieve your location: " + error.message, { type: "warning" });
//                    },
//                    {
//                        enableHighAccuracy: true,
//                        timeout: 10000,
//                        maximumAge: 0,
//                    }
//                );
//            } else {
//                console.warn("Geolocation not supported");
//                notification.add("Geolocation is not supported by your browser.", { type: "warning" });
//            }
//        }
//
//        // Run automatically after session is initialized
//        if (session.uid) {
//            captureLocation();
//        } else {
//            let attempts = 0;
//            const maxAttempts = 10;
//            const interval = setInterval(() => {
//                if (session.uid) {
//                    clearInterval(interval);
//                    captureLocation();
//                } else if (attempts >= maxAttempts) {
//                    clearInterval(interval);
//                    console.warn("Could not detect login session.");
//                    notification.add("Unable to detect user login.", { type: "warning" });
//                }
//                attempts++;
//            }, 1000);
//        }
//    },
//};
//
//// Register service
//registry.category("services").add("user_location", UserLocationService);
