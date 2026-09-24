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
const getAccessKey = () => `job_card_user_has_filter_access_${session?.uid || 0}`;

// Pre-cache user supervisor vs mobile status as soon as web client loads
patch(WebClient.prototype, {
    setup() {
        super.setup(...arguments);
        try {
            const user = useService("user");
            Promise.all([
                user.hasGroup("machine_repair_management.group_technical_allocation_user"),
                user.hasGroup("machine_repair_management.group_parts_supervisor_both"),
                user.hasGroup("machine_repair_management.group_parts_user"),
                user.hasGroup("machine_repair_management.group_job_card_back_office_user"),
                user.hasGroup("machine_repair_management.group_job_card_mobile_user"),
            ]).then(([isSupervisor, isPartsSupervisor, isParts, isBackOffice, isMobile]) => {
                const isSupervisorRole = isSupervisor || isPartsSupervisor || isParts || isBackOffice;
                const hasAccess = isSupervisorRole && !isMobile;
                sessionStorage.setItem(getAccessKey(), hasAccess ? "true" : "false");
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
            // Clear saved Job Card filters when visiting any other non-Job Card screen
            sessionStorage.removeItem(STORAGE_KEY_WC);
            sessionStorage.removeItem(STORAGE_KEY_TECH);
            sessionStorage.removeItem(STORAGE_KEY_POPULATED);
            return domain;
        }

        // Only apply populate filter to List (tree) view.
        // NEVER filter Kanban (mobile view), Form, Pivot, Graph, Calendar, etc.
        const viewType = this.config?.viewType || this.env.config?.viewType || "";
        if (viewType && viewType !== "list") {
            return domain;
        }

        // Never filter in dialogs / popups (e.g. Task Matches popup, modal dialogs, target="new")
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

        // If user is explicitly confirmed NOT to have filter access (e.g. mobile user or non-supervisor), return normal domain
        const accessCache = sessionStorage.getItem(getAccessKey());
        if (accessCache === "false" || (this.headerFilterState && this.headerFilterState.isInitialized && this.headerFilterState.hasFilterAccess === false)) {
            return domain;
        }

        // Check if returning from a form view via breadcrumbs vs opening menu fresh
        const breadcrumbs = this.env.config?.breadcrumbs || [];
        const isBreadcrumbReturn = breadcrumbs.length > 0;

        if (!isBreadcrumbReturn) {
            // Opening fresh from menu: clear previous session filters so page always starts empty
            sessionStorage.removeItem(STORAGE_KEY_WC);
            sessionStorage.removeItem(STORAGE_KEY_TECH);
            sessionStorage.removeItem(STORAGE_KEY_POPULATED);
        }

        const isPopulated =
            this.headerFilterState?.isPopulated ||
            (isBreadcrumbReturn && sessionStorage.getItem(STORAGE_KEY_POPULATED) === "true");

        if (!isPopulated) {
            // Display empty list view until supervisor clicks the 'Populate' button
            domain.push(["id", "=", 0]);
            return domain;
        }

        const wcIdStr =
            this.headerFilterState?.selectedWorkCenterId ||
            (isBreadcrumbReturn && sessionStorage.getItem(STORAGE_KEY_WC)) ||
            "";
        const wcId = parseInt(wcIdStr) || 0;

        const techIdStr =
            this.headerFilterState?.selectedTechnicianId ||
            (isBreadcrumbReturn && sessionStorage.getItem(STORAGE_KEY_TECH)) ||
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

        // Never enable workcenter / technician toolbar inside popup / dialog (e.g. Task Matches popup)
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

        // Check if returning from a form view via breadcrumbs vs opening menu fresh
        const breadcrumbs = this.env.config?.breadcrumbs || [];
        const isBreadcrumbReturn = breadcrumbs.length > 0;

        if (!isBreadcrumbReturn) {
            // Opening fresh from menu: clear previous session filters and populated status
            sessionStorage.removeItem(STORAGE_KEY_WC);
            sessionStorage.removeItem(STORAGE_KEY_TECH);
            sessionStorage.removeItem(STORAGE_KEY_POPULATED);
        }

        const savedWcId = isBreadcrumbReturn ? (sessionStorage.getItem(STORAGE_KEY_WC) || "") : "";
        const savedTechId = isBreadcrumbReturn ? (sessionStorage.getItem(STORAGE_KEY_TECH) || "") : "";
        const initialAccess = sessionStorage.getItem(getAccessKey());
        const initialPopulated = isBreadcrumbReturn && sessionStorage.getItem(STORAGE_KEY_POPULATED) === "true";

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
            // Fetch all support teams assigned to the selected work center
            const teams = await this.orm.searchRead(
                "machine.support.team",
                [["work_center_id", "=", parseInt(wcId)]],
                ["id", "name", "leader_id", "project_ids"]
            );

            if (userProjectIds.length === 0) {
                return teams;
            }

            // Filter technicians/teams matching both the work center and sharing project IDs with the logged-in user
            const validTeams = [];
            for (const team of teams) {
                let hasMatchingProject = false;

                // Check direct team project_ids if available
                if (team.project_ids && team.project_ids.some(pid => userProjectIds.includes(pid))) {
                    hasMatchingProject = true;
                }

                // Check leader_id (user) project_ids if available
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

            // Fallback to all work center teams if strict project mapping yields empty results
            return validTeams.length > 0 ? validTeams : teams;
        } catch (e) {
            console.error("Error fetching technicians for selected work center:", e);
            try {
                return await this.orm.searchRead(
                    "machine.support.team",
                    [["work_center_id", "=", parseInt(wcId)]],
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
            const [isTechAlloc, isPartsSupervisor, isParts, isBackOffice, isMobile] = await Promise.all([
                this.user.hasGroup("machine_repair_management.group_technical_allocation_user"),
                this.user.hasGroup("machine_repair_management.group_parts_supervisor_both"),
                this.user.hasGroup("machine_repair_management.group_parts_user"),
                this.user.hasGroup("machine_repair_management.group_job_card_back_office_user"),
                this.user.hasGroup("machine_repair_management.group_job_card_mobile_user"),
            ]);

            // Populate button and filter only apply to Supervisors/Back Office, NEVER to Mobile Users
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