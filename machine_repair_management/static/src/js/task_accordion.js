/** @odoo-module **/
 
// Define toggleFaq globally to support onclick="toggleFaq(this)"
// console.log("task_accordion.js loaded"); // Debug to confirm script loading
 
window.toggleFaq = function(btn) {
    // console.log("toggleFaq called with btn:", btn);
    const list = btn.parentElement.querySelector(".list");
    const icon = btn.querySelector(".accordion-icon");
    // console.log("List element:", list);
    // console.log("Icon element:", icon);
    if (!list) {
        console.warn("List element not found for btn:", btn);
        return;
    }
 
    const isHidden = list.style.display === "none" || list.style.display === "";
    console.log("Is hidden:", isHidden);
    list.style.display = isHidden ? "block" : "none";
 
    if (icon) {
        if (isHidden) {
            icon.classList.remove("fa-chevron-down");
            icon.classList.add("fa-check");
        } else {
            icon.classList.remove("fa-check");
            icon.classList.add("fa-chevron-down");
        }
        console.log("Icon classList after toggle:", icon.classList);
    }
};
 
// Debug to confirm toggleFaq is defined
// console.log("toggleFaq defined:", typeof window.toggleFaq === "function");
 