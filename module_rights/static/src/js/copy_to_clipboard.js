/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

/**
 * Copy text to the clipboard, returning whether it succeeded.
 *
 * The async Clipboard API only works in a secure context (https or
 * localhost). This app is served over plain http on a LAN host/IP
 * (e.g. http://122.165.5.171:8059 or http://saravanans-macbook-air.local:8069),
 * where navigator.clipboard is undefined — so fall back to the legacy
 * execCommand("copy") on a hidden textarea, which still works there. This is
 * why the earlier copy button "wasn't working" and was removed.
 *
 * @param {string} text
 * @returns {Promise<boolean>} true when the text was copied
 */
export async function copyToClipboard(text) {
    text = (text || "").trim();
    if (!text) {
        return false;
    }
    // Preferred path: async Clipboard API (secure contexts only).
    try {
        if (window.isSecureContext && browser.navigator.clipboard) {
            await browser.navigator.clipboard.writeText(text);
            return true;
        }
    } catch {
        // fall through to the legacy path
    }
    // Fallback path for insecure (http) contexts.
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "-1000px";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try {
        ok = document.execCommand("copy");
    } catch {
        ok = false;
    }
    document.body.removeChild(ta);
    return ok;
}
