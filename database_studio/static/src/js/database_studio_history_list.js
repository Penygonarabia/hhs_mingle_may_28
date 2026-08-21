/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { useState, onMounted, onPatched } from "@odoo/owl";
import { analyserRegistry, makeQtab } from "./database_studio_analyser";

// History splits into two tabs: queries the user explicitly starred (Save in
// the Analyser, or the star widget here) vs. every query Execute has run,
// logged automatically. Same underlying list/model — just a different domain.
function domainForHistoryTab(tab) {
    return [["is_favorite", "=", tab === "saved"]];
}

// Clicking a history row opens the Analyser with that query loaded, instead of
// the default form view.
export class SqlMsHistoryController extends ListController {
    setup() {
        super.setup();
        this.action = useService("action");
        // The action's own domain (see action_sql_ms_query in
        // database_studio_query_views.xml) already opens on the "saved"
        // tab; this just tracks which one is active for the button styling
        // and for reloading with the other tab's domain on click.
        this.histState = useState({ tab: "saved" });
        // The Saved/On-the-fly toggle is injected as plain DOM into the
        // control panel rather than through a custom t-inherit="web.ListView"
        // template. A template patch is only compiled lazily, on first use —
        // if it's broken (e.g. an xpath that doesn't match this build's
        // control panel layout), nothing errors until this component tries
        // to render, at which point it throws "Missing template" and the
        // action manager silently falls back to whatever opened it. Plain
        // DOM avoids that failure mode entirely and is simple enough here
        // that the safety of QWeb inheritance isn't worth the fragility.
        onMounted(() => this._renderHistTabs());
        onPatched(() => this._renderHistTabs());
    }

    _renderHistTabs() {
        const root = this.rootRef.el;
        const container = root && root.querySelector(".o_control_panel_main_buttons");
        if (!container || container.querySelector(".sqlms-hist-tabs")) {
            return;
        }
        const wrap = document.createElement("div");
        wrap.className = "sqlms-hist-tabs";
        const savedBtn = document.createElement("button");
        savedBtn.type = "button";
        savedBtn.textContent = "Saved queries";
        const onflyBtn = document.createElement("button");
        onflyBtn.type = "button";
        onflyBtn.textContent = "On the fly queries";
        const sync = () => {
            savedBtn.className = "btn btn-sm " +
                (this.histState.tab === "saved" ? "btn-primary" : "btn-secondary");
            onflyBtn.className = "btn btn-sm " +
                (this.histState.tab === "onfly" ? "btn-primary" : "btn-secondary");
        };
        savedBtn.addEventListener("click", () => this.setHistoryTab("saved", sync));
        onflyBtn.addEventListener("click", () => this.setHistoryTab("onfly", sync));
        sync();
        wrap.appendChild(savedBtn);
        wrap.appendChild(onflyBtn);
        container.appendChild(wrap);
    }

    setHistoryTab(tab, sync) {
        if (this.histState.tab === tab) {
            return;
        }
        this.histState.tab = tab;
        if (sync) {
            sync();
        }
        this.model.load({ domain: domainForHistoryTab(tab) });
    }

    // A tab already holding this history record: the same row is linked by
    // id, or — as the user sees it — a tab carrying the same name. Auto
    // labels ("Query 3") are never matched on, only names a record gave.
    _openTabFor(record, qtabs) {
        const name = (record.data.name || "").trim();
        return (qtabs || []).find(
            (qt) => (qt.historyId && qt.historyId === record.resId) ||
                (name && qt.fullName && qt.fullName.trim() === name)
        );
    }

    openRecord(record) {
        const query = record.data.query;
        // If this History list was opened from an Analyser (via its "Query
        // history" button), that Analyser stashed its tabs in the registry
        // before navigating here — so the picked query joins them, and the
        // next Analyser to mount picks up right where that one left off
        // instead of losing its other tabs. Otherwise start a plain new tab.
        // The tab is linked back to this record (name shown as its label,
        // Save updates it in place) whether it came from Saved or On-the-fly.
        const pending = analyserRegistry.pending;
        // Picking a query that is already open just brings its tab forward.
        // Opening a second tab on the same query would leave two of them to
        // keep in step, and the one being edited would not be obvious. Its
        // text is left as it stands: that tab may hold unsaved edits, and
        // silently resetting them to the stored query would lose work.
        const open = pending && this._openTabFor(record, pending.qtabs);
        if (open) {
            pending.activeQtabId = open.id;
            pending.ts = Date.now();
        } else {
            const tab = makeQtab(query, {
                name: record.data.name,
                historyId: record.resId,
                isSaved: !!record.data.is_favorite,
            });
            if (pending) {
                pending.qtabs.push(tab);
                pending.activeQtabId = tab.id;
                pending.ts = Date.now();
            } else {
                analyserRegistry.pending = {
                    qtabs: [tab],
                    activeQtabId: tab.id,
                    ts: Date.now(),
                };
            }
        }
        this.action.doAction({
            type: "ir.actions.client",
            tag: "database_studio.analyser",
            name: "Analyser",
        });
    }
}

registry.category("views").add("database_studio_history_list", {
    ...listView,
    Controller: SqlMsHistoryController,
});
