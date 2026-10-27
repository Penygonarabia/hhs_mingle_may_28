/** @odoo-module **/

import { PhonePopupListController } from "@machine_repair_management/js/phone_popup_list_controller";
import { SearchModel } from "@web/search/search_model";
import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { useState, onWillStart } from "@odoo/owl";

const STORAGE_KEY_WC = "job_card_selected_wc_id";
const STORAGE_KEY_TECH = "job_card_selected_tech_id";
const STORAGE_KEY_POPULATED = "job_card_is_populated";
const STORAGE_KEY_USER_WC_COUNT = `job_card_user_wc_count_${session?.uid || 0}`;
const STORAGE_KEY_USER_SINGLE_WC_ID = `job_card_user_single_wc_id_${session?.uid || 0}`;
const getAccessKey = () => `job_card_user_has_filter_access_${session?.uid || 0}`;

// Pre-cache access rights AND work centers on WebClient startup
patch(WebClient.prototype, {
    setup() {
        super.setup(...arguments);
        try {
            const user = useService("user");
            const orm = useService("orm");

            Promise.all([
                user.hasGroup("machine_repair_management.group_technical_allocation_user"),
                user.hasGroup("machine_repair_management.group_parts_supervisor_both"),
                user.hasGroup("machine_repair_management.group_parts_user"),
                user.hasGroup("machine_repair_management.group_job_card_back_office_user"),
                user.hasGroup("machine_repair_management.group_job_card_mobile_user"),
                orm.read("res.users", [session.uid], ["default_work_center_id"]),
            ]).then(([isSupervisor, isPartsSupervisor, isParts, isBackOffice, isMobile, userData]) => {
                const isSupervisorRole = isSupervisor || isPartsSupervisor || isParts || isBackOffice;
                const hasAccess = isSupervisorRole && !isMobile;
                sessionStorage.setItem(getAccessKey(), hasAccess ? "true" : "false");

                // Parse Work Center IDs
                let rawWc = userData[0]?.default_work_center_id || [];
                let assignedWcIds = [];
                if (Array.isArray(rawWc)) {
                    if (rawWc.length > 0 && typeof rawWc[0] === "number" && typeof rawWc[1] === "string") {
                        assignedWcIds = [rawWc[0]]; // Many2one
                    } else {
                        assignedWcIds = rawWc; // Many2many
                    }
                } else if (typeof rawWc === "number") {
                    assignedWcIds = [rawWc];
                }

                sessionStorage.setItem(STORAGE_KEY_USER_WC_COUNT, assignedWcIds.length.toString());
                if (assignedWcIds.length === 1) {
                    sessionStorage.setItem(STORAGE_KEY_USER_SINGLE_WC_ID, assignedWcIds[0].toString());
                } else {
                    sessionStorage.removeItem(STORAGE_KEY_USER_SINGLE_WC_ID);
                }
            }).catch(() => {});
        } catch (e) {}
    },
});

// Safely capture original domain getter from SearchModel prototype
const originalDomainGetter = Object.getOwnPropertyDescriptor(SearchModel.prototype, "domain")?.get;

// Patch SearchModel to dynamically include Work Center and Technician domains
patch(SearchModel.prototype, {
    get domain() {
        const domain = originalDomainGetter ? [...originalDomainGetter.call(this)] : [];
        const modelName = this.resModel || this.config?.resModel || "";

        if (modelName !== "project.task") {
            sessionStorage.removeItem(STORAGE_KEY_WC);
            sessionStorage.removeItem(STORAGE_KEY_TECH);
            sessionStorage.removeItem(STORAGE_KEY_POPULATED);
            return domain;
        }

        const viewType = this.config?.viewType || this.env.config?.viewType || "";
        if (viewType && viewType !== "list") {
            return domain;
        }

        // Never filter inside popups or modals
        const isInDialog = Boolean(
            this.env?.inDialog ||
            this.env?.dialogData ||
            this.config?.target === "new" ||
            this.env.config?.target === "new" ||
            this.context?.show_update_button ||
            this.context?.target === "new" ||
            this.env.config?.actionName === "Task Matches" ||
            this.env.config?.action?.name === "Task Matches" ||
            (this.headerFilterState && this.headerFilterState.isInDialog)
        );
        if (isInDialog) {
            return domain;
        }

        const accessCache = sessionStorage.getItem(getAccessKey());
        if (accessCache === "false" || (this.headerFilterState && this.headerFilterState.isInitialized && this.headerFilterState.hasFilterAccess === false)) {
            return domain;
        }

        // Check if single work center is cached
        const singleWcId = sessionStorage.getItem(STORAGE_KEY_USER_SINGLE_WC_ID);
        const wcCount = parseInt(sessionStorage.getItem(STORAGE_KEY_USER_WC_COUNT) || "0", 10);
        const isSingleCenterUser = wcCount === 1 && singleWcId;

        const isPopulated =
            this.headerFilterState?.isPopulated ||
            sessionStorage.getItem(STORAGE_KEY_POPULATED) === "true" ||
            isSingleCenterUser;

        // If user has multiple work centers and hasn't clicked Populate yet, hide records
        if (!isPopulated) {
            domain.push(["id", "=", 0]);
            return domain;
        }

        const wcIdStr =
            this.headerFilterState?.selectedWorkCenterId ||
            sessionStorage.getItem(STORAGE_KEY_WC) ||
            (isSingleCenterUser ? singleWcId : "");
        const wcId = parseInt(wcIdStr, 10) || 0;

        const techIdStr =
            this.headerFilterState?.selectedTechnicianId ||
            sessionStorage.getItem(STORAGE_KEY_TECH) ||
            "";
        const techId = parseInt(techIdStr, 10) || 0;

        if (wcId || techId) {
            if (wcId) {
                domain.push(["work_center_id", "=", wcId]);
            }
            if (techId) {
                domain.push(["team_id", "=", techId]);
            }
        } else {
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

        const isInDialog = Boolean(
            this.env.inDialog ||
            this.env.dialogData ||
            this.props?.context?.show_update_button ||
            this.props?.target === "new" ||
            this.env.config?.target === "new" ||
            this.env.config?.actionName === "Task Matches" ||
            this.env.config?.action?.name === "Task Matches" ||
            this.props?.title === "Task Matches" ||
            (this.env.searchModel?.context?.show_update_button)
        );

        if (isInDialog) {
            this.filterState = useState({
                hasFilterAccess: false,
                isInDialog: true,
            });
            if (this.env.searchModel) {
                this.env.searchModel.headerFilterState = this.filterState;
            }
            return;
        }

        const breadcrumbs = this.env.config?.breadcrumbs || [];
        const isBreadcrumbReturn = breadcrumbs.length > 0;

        if (!isBreadcrumbReturn) {
            sessionStorage.removeItem(STORAGE_KEY_WC);
            sessionStorage.removeItem(STORAGE_KEY_TECH);
            sessionStorage.removeItem(STORAGE_KEY_POPULATED);
        }

        const singleWcId = sessionStorage.getItem(STORAGE_KEY_USER_SINGLE_WC_ID);
        const wcCount = parseInt(sessionStorage.getItem(STORAGE_KEY_USER_WC_COUNT) || "0", 10);
        const isSingleCenterUser = wcCount === 1 && singleWcId;

        const savedWcId = isBreadcrumbReturn 
            ? (sessionStorage.getItem(STORAGE_KEY_WC) || "") 
            : (isSingleCenterUser ? singleWcId : "");

        const savedTechId = isBreadcrumbReturn 
            ? (sessionStorage.getItem(STORAGE_KEY_TECH) || "") 
            : "";

        const initialAccess = sessionStorage.getItem(getAccessKey());
        const initialPopulated = (isBreadcrumbReturn && sessionStorage.getItem(STORAGE_KEY_POPULATED) === "true") || isSingleCenterUser;

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
        const userProjectIds = this.filterState.userProjectIds || [];

        try {
            const teams = await this.orm.searchRead(
                "machine.support.team",
                [["work_center_id", "=", parseInt(wcId, 10)]],
                ["id", "name", "leader_id", "project_ids"]
            );

            if (userProjectIds.length === 0) {
                return teams;
            }

            const validTeams = [];
            for (const team of teams) {
                let hasMatchingProject = false;

                if (team.project_ids && team.project_ids.some(pid => userProjectIds.includes(pid))) {
                    hasMatchingProject = true;
                }

                if (!hasMatchingProject && team.leader_id && team.leader_id[0]) {
                    const leaderData = await this.orm.read(
                        "res.users",
                        [team.leader_id[0]],
                        ["project_ids"]
                    );
                    const leaderProjects = leaderData[0]?.project_ids || [];
                    if (leaderProjects.some(pid => userProjectIds.includes(pid))) {
                        hasMatchingProject = true;
                    }
                }

                if (hasMatchingProject) {
                    validTeams.push(team);
                }
            }

            return validTeams.length > 0 ? validTeams : teams;
        } catch (e) {
            console.error("Error fetching technicians for selected work center:", e);
            try {
                return await this.orm.searchRead(
                    "machine.support.team",
                    [["work_center_id", "=", parseInt(wcId, 10)]],
                    ["id", "name", "leader_id"]
                );
            } catch (err) {
                return [];
            }
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

   /* _triggerSearchReload() {
        if (this.env.searchModel) {
            if (typeof this.env.searchModel.search === "function") {
                this.env.searchModel.search();
                return;
            } else if (typeof this.env.searchModel._notify === "function") {
                this.env.searchModel._notify();
                return;
            } else if (typeof this.env.searchModel.trigger === "function") {
                this.env.searchModel.trigger("update");
                return;
            }
        }

        // Safe fallback passing the existing config to avoid the orderBy undefined error
        if (this.model && typeof this.model.load === "function") {
            const config = this.model.root?.config || { orderBy: [] };
            this.model.load(config);
        }
    },*/
	
	_triggerSearchReload() {
	        // In Odoo List Views, notify the searchModel or list root
	        if (this.env.searchModel && typeof this.env.searchModel._notify === "function") {
	            this.env.searchModel._notify();
	        } else if (this.model?.root && typeof this.model.root.load === "function") {
	            this.model.root.load();
	        }
	    },

    async _initWorkCenterFilter() {
        try {
            const [isTechAlloc, isPartsSupervisor, isParts, isBackOffice, isMobile] = await Promise.all([
                this.user.hasGroup("machine_repair_management.group_technical_allocation_user"),
                this.user.hasGroup("machine_repair_management.group_parts_supervisor_both"),
                this.user.hasGroup("machine_repair_management.group_parts_user"),
                this.user.hasGroup("machine_repair_management.group_job_card_back_office_user"),
                this.user.hasGroup("machine_repair_management.group_job_card_mobile_user"),
            ]);

            const isSupervisorRole = isTechAlloc || isPartsSupervisor || isParts || isBackOffice;
            const hasAccess = isSupervisorRole && !isMobile;
            const accessChanged = this.filterState.hasFilterAccess !== hasAccess;

            this.filterState.hasFilterAccess = hasAccess;
            this.filterState.isInitialized = true;
            sessionStorage.setItem(getAccessKey(), hasAccess ? "true" : "false");

            if (!hasAccess) {
                if (accessChanged) {
                    this._triggerSearchReload();
                }
                return;
            }

            this.filterState.isCoordinator = isBackOffice;

            const userData = await this.orm.read(
                "res.users",
                [this.user.userId],
                ["default_work_center_id", "project_ids"]
            );

            let rawWc = userData[0]?.default_work_center_id || [];
            let assignedWcIds = [];
            if (Array.isArray(rawWc)) {
                if (rawWc.length > 0 && typeof rawWc[0] === "number" && typeof rawWc[1] === "string") {
                    assignedWcIds = [rawWc[0]];
                } else {
                    assignedWcIds = rawWc;
                }
            } else if (typeof rawWc === "number") {
                assignedWcIds = [rawWc];
            }

            const userProjectIds = userData[0]?.project_ids || [];
            this.filterState.userProjectIds = userProjectIds;

            sessionStorage.setItem(STORAGE_KEY_USER_WC_COUNT, assignedWcIds.length.toString());

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

            // CASE 1: EXACTLY ONE WORK CENTER
			// CASE 1: EXACTLY ONE WORK CENTER
			    if (this.filterState.workCenters.length === 1) {
			        const singleWc = this.filterState.workCenters[0];
			        const singleWcId = String(singleWc.id);

			        sessionStorage.setItem(STORAGE_KEY_USER_SINGLE_WC_ID, singleWcId);
			        sessionStorage.setItem(STORAGE_KEY_WC, singleWcId);
			        sessionStorage.setItem(STORAGE_KEY_POPULATED, "true");

			        this.filterState.selectedWorkCenterId = singleWcId;
			        this.filterState.isPopulated = true;

			        this.filterState.technicians = await this._fetchTechnicians(singleWcId);

			        // Only reload if the list hasn't loaded records yet
			        if (!this.model?.root?.records?.length) {
			            this._triggerSearchReload();
			        }
			    }
            // CASE 2: MULTIPLE WORK CENTERS
            else {
                sessionStorage.removeItem(STORAGE_KEY_USER_SINGLE_WC_ID);

                // If restored from breadcrumbs with a previously populated state
                if (this.filterState.selectedWorkCenterId && this.filterState.isPopulated) {
                    this.filterState.technicians = await this._fetchTechnicians(this.filterState.selectedWorkCenterId);
                } else {
                    // Blank view until user selects and clicks POPULATE
                    this.filterState.isPopulated = false;
                    sessionStorage.removeItem(STORAGE_KEY_POPULATED);
                }
            }
        } catch (err) {
            console.error("Error initializing Work Center filter:", err);
            this.filterState.isInitialized = true;
        }
    },
});