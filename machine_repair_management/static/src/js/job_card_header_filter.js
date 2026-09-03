/** @odoo-module **/

import { PhonePopupListController } from "@machine_repair_management/js/phone_popup_list_controller";
import { SearchModel } from "@web/search/search_model";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillStart } from "@odoo/owl";

const STORAGE_KEY_WC = "job_card_selected_wc_id";
const STORAGE_KEY_TECH = "job_card_selected_tech_id";
const STORAGE_KEY_ACCESS = "job_card_user_has_filter_access";
const STORAGE_KEY_POPULATED = "job_card_is_populated";

// Safely capture original domain getter from SearchModel prototype
const originalDomainGetter = Object.getOwnPropertyDescriptor(SearchModel.prototype, "domain")?.get;

// Patch SearchModel to dynamically include Work Center and Technician domains
patch(SearchModel.prototype, {
    get domain() {
        const domain = originalDomainGetter ? [...originalDomainGetter.call(this)] : [];
        const modelName = this.resModel || this.config?.resModel || "";

        if (modelName !== "project.task") {
            // Clear saved Job Card filters when visiting any other non-Job Card screen
            sessionStorage.removeItem(STORAGE_KEY_WC);
            sessionStorage.removeItem(STORAGE_KEY_TECH);
            sessionStorage.removeItem(STORAGE_KEY_POPULATED);
            return domain;
        }

        // Check cached filter access status from sessionStorage
        const accessCache = sessionStorage.getItem(STORAGE_KEY_ACCESS);

        // If user is explicitly confirmed NOT to have filter access (e.g. mobile user), return normal domain as usual
        if (accessCache === "false" || (this.headerFilterState && this.headerFilterState.isInitialized && this.headerFilterState.hasFilterAccess === false)) {
            return domain;
        }

        // If accessCache is null (first load before group check finishes), default to standard domain until group check completes
        if (accessCache === null && (!this.headerFilterState || !this.headerFilterState.isInitialized)) {
            return domain;
        }

        const isPopulated =
            this.headerFilterState?.isPopulated ||
            sessionStorage.getItem(STORAGE_KEY_POPULATED) === "true";

        if (!isPopulated) {
            // Display empty list view until user clicks the 'Populate' button
            domain.push(["id", "=", 0]);
            return domain;
        }

        const wcIdStr =
            this.headerFilterState?.selectedWorkCenterId ||
            sessionStorage.getItem(STORAGE_KEY_WC) ||
            "";
        const wcId = parseInt(wcIdStr) || 0;

        const techIdStr =
            this.headerFilterState?.selectedTechnicianId ||
            sessionStorage.getItem(STORAGE_KEY_TECH) ||
            "";
        const techId = parseInt(techIdStr) || 0;

        if (wcId || techId) {
            if (wcId) {
                domain.push(["work_center_id", "=", wcId]);
            }
            if (techId) {
                domain.push(["team_id", "=", techId]);
            }
        } else {
            // Display empty list view when NEITHER Work Center nor Technician is selected
            domain.push(["id", "=", 0]);
        }

        return domain;
    },
});

patch(PhonePopupListController.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.user = useService("user");

        // Check if returning from a form view via breadcrumbs vs opening menu fresh
        const breadcrumbs = this.env.config?.breadcrumbs || [];
        const isBreadcrumbReturn = breadcrumbs.length > 0;

        if (!isBreadcrumbReturn) {
            // Opening fresh from menu: clear previous session filters and populated status
            sessionStorage.removeItem(STORAGE_KEY_WC);
            sessionStorage.removeItem(STORAGE_KEY_TECH);
            sessionStorage.removeItem(STORAGE_KEY_POPULATED);
        }

        const savedWcId = sessionStorage.getItem(STORAGE_KEY_WC) || "";
        const savedTechId = sessionStorage.getItem(STORAGE_KEY_TECH) || "";
        const initialAccess = sessionStorage.getItem(STORAGE_KEY_ACCESS);
        const initialPopulated = sessionStorage.getItem(STORAGE_KEY_POPULATED) === "true";

        this.filterState = useState({
            workCenters: [],
            technicians: [],
            selectedWorkCenterId: savedWcId,
            selectedTechnicianId: savedTechId,
            isPopulated: initialPopulated,
            userProjectIds: [],
            isCoordinator: false,
            hasFilterAccess: initialAccess === "true" ? true : (initialAccess === "false" ? false : null),
            isInitialized: initialAccess !== null,
        });

        if (this.env.searchModel) {
            this.env.searchModel.headerFilterState = this.filterState;
        }

        onWillStart(async () => {
            await this._initWorkCenterFilter();
        });
    },

    async _fetchTechnicians(wcId) {
        if (!wcId) {
            return [];
        }
        const domain = [["work_center_id", "=", parseInt(wcId)]];
        if (this.filterState.userProjectIds && this.filterState.userProjectIds.length > 0) {
            domain.push(["project_ids", "in", this.filterState.userProjectIds]);
        }
        try {
            return await this.orm.searchRead(
                "machine.support.team",
                domain,
                ["id", "name", "leader_id"]
            );
        } catch (e) {
            console.error("Error fetching technicians for selected work center:", e);
            return [];
        }
    },

    async onWorkCenterChange(ev) {
        const wcId = ev.target.value;
        this.filterState.selectedWorkCenterId = wcId;
        this.filterState.selectedTechnicianId = "";
        this.filterState.technicians = [];

        if (wcId) {
            this.filterState.technicians = await this._fetchTechnicians(wcId);
        }
    },

    async onTechnicianChange(ev) {
        const techId = ev.target.value;
        this.filterState.selectedTechnicianId = techId;
    },

    async onPopulateClick() {
        const wcId = this.filterState.selectedWorkCenterId;
        const techId = this.filterState.selectedTechnicianId;

        if (wcId) {
            sessionStorage.setItem(STORAGE_KEY_WC, wcId);
        } else {
            sessionStorage.removeItem(STORAGE_KEY_WC);
        }

        if (techId) {
            sessionStorage.setItem(STORAGE_KEY_TECH, techId);
        } else {
            sessionStorage.removeItem(STORAGE_KEY_TECH);
        }

        this.filterState.isPopulated = true;
        sessionStorage.setItem(STORAGE_KEY_POPULATED, "true");

        this._triggerSearchReload();
    },

    _triggerSearchReload() {
        if (this.env.searchModel) {
            if (typeof this.env.searchModel.search === "function") {
                this.env.searchModel.search();
            } else if (typeof this.env.searchModel._notify === "function") {
                this.env.searchModel._notify();
            } else if (typeof this.env.searchModel.trigger === "function") {
                this.env.searchModel.trigger("update");
            }
        }
        if (this.model && typeof this.model.load === "function") {
            this.model.load();
        }
    },

    async _initWorkCenterFilter() {
        try {
            const [isTechAlloc, isParts, isBackOffice, isMobile] = await Promise.all([
                this.user.hasGroup("machine_repair_management.group_technical_allocation_user"),
                this.user.hasGroup("machine_repair_management.group_parts_user"),
                this.user.hasGroup("machine_repair_management.group_job_card_back_office_user"),
                this.user.hasGroup("machine_repair_management.group_job_card_mobile_user"),
            ]);

            const hasAccess = (isTechAlloc || isParts || isBackOffice) && !isMobile;
            const accessChanged = this.filterState.hasFilterAccess !== hasAccess;

            this.filterState.hasFilterAccess = hasAccess;
            this.filterState.isInitialized = true;
            sessionStorage.setItem(STORAGE_KEY_ACCESS, hasAccess ? "true" : "false");

            if (!hasAccess) {
                if (accessChanged) {
                    this._triggerSearchReload();
                }
                return;
            }

            this.filterState.isCoordinator = isBackOffice;

            const userData = await this.orm.read("res.users", [this.user.userId], ["default_work_center_id", "project_ids"]);
            const assignedWcIds = userData[0]?.default_work_center_id || [];
            const userProjectIds = userData[0]?.project_ids || [];
            this.filterState.userProjectIds = userProjectIds;

            if (assignedWcIds.length > 0) {
                this.filterState.workCenters = await this.orm.searchRead(
                    "work.center.location",
                    [["id", "in", assignedWcIds]],
                    ["id", "name"]
                );
            } else {
                this.filterState.workCenters = await this.orm.searchRead(
                    "work.center.location",
                    [],
                    ["id", "name"]
                );
            }

            // If a Work Center was restored from session (e.g. returning via breadcrumbs), fetch its technicians
            if (this.filterState.selectedWorkCenterId) {
                this.filterState.technicians = await this._fetchTechnicians(this.filterState.selectedWorkCenterId);
            }
        } catch (err) {
            console.error("Error initializing Work Center filter:", err);
            this.filterState.isInitialized = true;
        }
    },
});
