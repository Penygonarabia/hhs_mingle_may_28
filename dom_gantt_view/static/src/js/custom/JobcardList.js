/** @odoo-module **/

import { Component, useState, useRef, onMounted, onPatched, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { FilterDialog } from "./filter_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";

const STORAGE_KEY_WC = "job_card_sch_selected_wc_id";
const STORAGE_KEY_TECH = "job_card_sch_selected_tech_id";
const STORAGE_KEY_USER = "job_card_sch_selected_user_id";
const STORAGE_KEY_POPULATED = "job_card_sch_is_populated";

const ALLOWED_JOB_CARD_STATES = [
  "101", // New
  "107", // Rescheduled
  "117", // Unit Pull Out
  "132", // Unit Ready For Delivery
  "122", // Parts Ready & Rescheduled
  "152",
  "156",
  "207",
];

export class JobcardList extends Component {
  static template = "JobcardList";

  get isRTL() {
    const lang = (this.user?.lang || session?.user_context?.lang || "").toLowerCase();
    const docDir = document.documentElement.getAttribute("dir") || document.body.getAttribute("dir");
    return lang.startsWith("ar") || docDir === "rtl";
  }

  get isAmcProject() {
    return this.state.project_id === 4;
  }

  setup() {
    this.orm = useService("orm");
    this.notification = useService("notification");
    this.actionService = useService("action");
    this.dialog = useService("dialog");
    this.user = useService("user");

    const context = this.env.context || {};
    this.hideJobCardList = context.hide_jobcard_list || false;

    // Reset session filters when opening fresh from menu
    const breadcrumbs = this.env.config?.breadcrumbs || [];
    if (breadcrumbs.length === 0) {
      sessionStorage.removeItem(STORAGE_KEY_WC);
      sessionStorage.removeItem(STORAGE_KEY_TECH);
      sessionStorage.removeItem(STORAGE_KEY_USER);
      sessionStorage.removeItem(STORAGE_KEY_POPULATED);
    }

    const savedWcId = sessionStorage.getItem(STORAGE_KEY_WC) || "";
    const savedTechId = sessionStorage.getItem(STORAGE_KEY_TECH) || "";
    const initialPopulated = sessionStorage.getItem(STORAGE_KEY_POPULATED) === "true";

    this.state = useState({
      language: session.user_context.lang || "en_US",
      showTable: false,
      jobCards: [],
      jobcardId: null,
      jobCardNumber: "",
      name: "",
      customerName: "",
      serviceDatetime: "",
      planned_date_begin: null,
      planned_date_end: null,
      user_ids: [],
      teamId: null,
      technicianName: null,
      job_card_state_code: null,
      job_state: null,
      job_card_state: "",
      service_requested_datetime_formatted: "",
      selectedJobCardId: null,
      cityList: [],
      selectedCityId: null,
      selectedStatusCode: null,
      availableCities: [],
      combinedCities: [],
      loadedJobcardStates: [],
      workCenterList: [],
      selectedWorkcenterId: savedWcId,
      technicians: [],
      selectedTechnicianId: savedTechId,
      userProjectIds: [],
      isPopulated: initialPopulated,
      contractList: [],
      selectedContractId: null,
      project_related_amc_bool: false,
      isAmcProject: false,
      project_id: null,
    });

    this.userMap = {};
    this.hasSlotClicked = false;
    this.cardListRef = useRef("cardList");

    onMounted(async () => {
      this._applyDirection();
      await this.loadUsers();
      await this._initWorkCenterFilter();

      if (this.state.isPopulated && this.state.selectedWorkcenterId) {
        this.state.technicians = await this._fetchTechnicians(this.state.selectedWorkcenterId);
        await this.loadJobCards();
        await this.loadCities();
        await this.loadedJobcardStates();
        await this.loadContracts();
      }
      this.attachHighlightHandler();
    });

    onPatched(() => {
      this._applyDirection();
    });

    if (this.env?.bus) {
      useBus(this.env.bus, "jobcard-selected", (event) => {
        this.updateSelectedJobCard(event.detail, false);
      });

      useBus(this.env.bus, "slot-clicked", (event) => {
        if (!this.hasSlotClicked) {
          this.hasSlotClicked = true;
          this.updateSelectedJobCard(event.detail, true);
        }
      });

      useBus(this.env.bus, "jobcard-unassigned", async () => {
        if (this.state.isPopulated) {
          await this.loadJobCards();
        }
        await new Promise((resolve) => setTimeout(resolve, 2000));
      });

      // Synchronize with the active project in top dropdown
      useBus(this.env.bus, "project-filter-updated", async (payload) => {
        const projectId = payload?.detail?.project_id || false;
        this.state.project_id = projectId ? parseInt(projectId, 10) : null;

        if (this.state.selectedWorkcenterId) {
          this.state.technicians = await this._fetchTechnicians(this.state.selectedWorkcenterId);

          if (this.state.selectedTechnicianId) {
            const exists = this.state.technicians.some(
              (t) => String(t.id) === String(this.state.selectedTechnicianId)
            );
            if (!exists) {
              this.state.selectedTechnicianId = "";
              sessionStorage.removeItem(STORAGE_KEY_TECH);
              sessionStorage.removeItem(STORAGE_KEY_USER);
            }
          }
        }

        if (this.state.isPopulated) {
          await this.loadJobCards();
          await this.loadedJobcardStates();
        }
      });
    }
  }

  _applyDirection() {
    if (this.cardListRef.el) {
      this.cardListRef.el.style.direction = this.isRTL ? "rtl" : "ltr";
      this.cardListRef.el.style.textAlign = this.isRTL ? "right" : "left";
    }
  }

  resetSelectedJobCard() {
    this.state.selectedJobCardId = null;
    this.state.name = "";
    this.state.customerName = "";
    this.state.service_requested_datetime_formatted = "";
  }

  async _initWorkCenterFilter() {
    try {
      const userData = await this.orm.read(
        "res.users",
        [this.user.userId],
        ["default_work_center_id", "project_ids"]
      );
      const assignedWcIds = userData[0]?.default_work_center_id || [];
      this.state.userProjectIds = userData[0]?.project_ids || [];

      if (assignedWcIds.length > 0) {
        this.state.workCenterList = await this.orm.searchRead(
          "work.center.location",
          [["id", "in", assignedWcIds]],
          ["id", "name"]
        );
      } else {
        this.state.workCenterList = await this.orm.searchRead(
          "work.center.location",
          [],
          ["id", "name"]
        );
      }

      if (this.state.selectedWorkcenterId) {
        this.state.technicians = await this._fetchTechnicians(this.state.selectedWorkcenterId);
      }
    } catch (err) {
      console.error("Error initializing Work Center filter:", err);
      this.state.workCenterList = [];
    }
  }

  async _fetchTechnicians(wcId) {
    if (!wcId) return [];

    try {
      const [wc] = await this.orm.read(
        "work.center.location",
        [parseInt(wcId, 10)],
        ["id", "work_center_group_id"]
      );

      let targetWcIds = [parseInt(wcId, 10)];
      const groupId = wc?.work_center_group_id?.[0];
      if (groupId) {
        const groupWcs = await this.orm.searchRead(
          "work.center.location",
          [["work_center_group_id", "=", groupId]],
          ["id"]
        );
        if (groupWcs.length) {
          targetWcIds = groupWcs.map((w) => w.id);
        }
      }

      const jobCardGroup = await this.orm.searchRead(
        "res.groups",
        [["name", "=", "Job Card Mobile User"]],
        ["id"]
      );
      const jobCardGroupId = jobCardGroup?.[0]?.id;

      const userDomain = [
        ["active", "=", true],
        ["share", "=", false],
        ["default_work_center_id", "in", targetWcIds],
      ];

      if (jobCardGroupId) {
        userDomain.push(["groups_id", "in", [jobCardGroupId]]);
      }

      // Filter technicians by selected project or user's project_ids
      const activeProjectId = this.state.project_id;
      if (activeProjectId) {
        userDomain.push(["project_ids", "in", [parseInt(activeProjectId, 10)]]);
      } else if (this.state.userProjectIds && this.state.userProjectIds.length > 0) {
        userDomain.push(["project_ids", "in", this.state.userProjectIds]);
      }

      return await this.orm.searchRead(
        "res.users",
        userDomain,
        ["id", "name", "display_name"]
      );
    } catch (e) {
      console.error("Error fetching technicians for work center:", e);
      return [];
    }
  }

  async onWorkcenterFilterChange(ev) {
    const wcId = ev.target.value;
    this.state.selectedWorkcenterId = wcId;
    this.state.selectedTechnicianId = "";
    this.state.technicians = [];
    this.state.isPopulated = false;
    this.state.jobCards = [];

    sessionStorage.removeItem(STORAGE_KEY_POPULATED);
    sessionStorage.removeItem(STORAGE_KEY_TECH);
    sessionStorage.removeItem(STORAGE_KEY_USER);

    if (wcId) {
      sessionStorage.setItem(STORAGE_KEY_WC, wcId);
      this.state.technicians = await this._fetchTechnicians(wcId);
    } else {
      sessionStorage.removeItem(STORAGE_KEY_WC);
    }

    this.env.bus.trigger("jobcard-filter-populated", { isPopulated: false });
  }

  async onTechnicianChange(ev) {
    const techId = ev.target.value;
    this.state.selectedTechnicianId = techId;
    if (techId) {
      sessionStorage.setItem(STORAGE_KEY_TECH, techId);
      sessionStorage.setItem(STORAGE_KEY_USER, techId);
    } else {
      sessionStorage.removeItem(STORAGE_KEY_TECH);
      sessionStorage.removeItem(STORAGE_KEY_USER);
    }

    if (this.state.isPopulated && this.env?.bus) {
      this.env.bus.trigger("jobcard-filter-populated", {
        isPopulated: true,
        workCenterId: this.state.selectedWorkcenterId,
        technicianUserId: techId ? parseInt(techId, 10) : null,
      });
    }
  }

  async onPopulateClick() {
    const wcId = this.state.selectedWorkcenterId;
    if (!wcId) {
      this.notification.add("Please select a Work Center before populating.", { type: "warning" });
      return;
    }

    sessionStorage.setItem(STORAGE_KEY_WC, wcId);

    const techUserId = this.state.selectedTechnicianId;
    if (techUserId) {
      sessionStorage.setItem(STORAGE_KEY_TECH, techUserId);
      sessionStorage.setItem(STORAGE_KEY_USER, String(techUserId));
    } else {
      sessionStorage.removeItem(STORAGE_KEY_TECH);
      sessionStorage.removeItem(STORAGE_KEY_USER);
    }

    this.state.isPopulated = true;
    sessionStorage.setItem(STORAGE_KEY_POPULATED, "true");

    // 1. Load left-side Job Cards based ONLY on Work Center & Project (Technician selection does not affect this)
    await this.loadJobCards();
    await this.loadCities();
    await this.loadedJobcardStates();
    await this.loadContracts();

    // 2. Filter right-side Assignees on the Gantt chart by the selected technician (or all if none selected)
    this.env.bus.trigger("jobcard-filter-populated", {
      isPopulated: true,
      workCenterId: wcId,
      technicianUserId: techUserId || null,
    });

    this.notification.add("Job cards and assignees populated successfully.", { type: "success" });
  }

  async openFilterDialog() {
    try {
      if (!this.state.combinedCities.length) {
        await this.loadCities();
      }
      if (!this.state.loadedJobcardStates?.length) {
        await this.loadedJobcardStates();
      }

      this.dialog.add(FilterDialog, {
        title: "Filter Job Cards",
        cityList: this.state.combinedCities,
        jobStates: this.state.loadedJobcardStates,
        onApply: (filters) => this.applyFilter(filters),
      });
    } catch (error) {
      console.error("Error opening filter dialog:", error);
      this.notification.add("Failed to open filter dialog.", { type: "danger" });
    }
  }

  async applyFilter(filters) {
    try {
      if (!this.state.isPopulated) return;
      const domain = [["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES]];

      if (filters.city && !isNaN(parseInt(filters.city, 10))) {
        domain.push(["customer_city_id", "=", parseInt(filters.city, 10)]);
      }

      if (filters.status && !isNaN(parseInt(filters.status, 10))) {
        domain.push(["job_card_state_id", "=", parseInt(filters.status, 10)]);
      }

      const jobCards = await this.orm.searchRead("project.task", domain, [
        "name",
        "customer_city_id",
        "job_card_state_id",
      ]);

      this.state.jobCards = jobCards;

      if (!jobCards.length) {
        this.notification.add("No job cards found for the selected filters.", { type: "info" });
      } else {
        this.notification.add(`✅ ${jobCards.length} job cards loaded successfully.`, { type: "success" });
      }
    } catch (error) {
      this.notification.add("Failed to apply filters.", { type: "danger" });
    }
  }

  async loadCities() {
    if (!this.state.isPopulated) return;
    try {
      const work_center_ids = this.state.selectedWorkcenterId ? [parseInt(this.state.selectedWorkcenterId, 10)] : [];
      if (!work_center_ids.length) return;

      const cityRecords = await this.orm.searchRead(
        "res.city",
        [["def_work_center_id", "in", work_center_ids]],
        ["id", "name"],
      );
      const allCityIds = cityRecords.map((c) => Number(c.id));
      if (!allCityIds.length) return;

      const domain = [
        "&",
        ["customer_city_id", "in", allCityIds],
        "|",
        ["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES],
        "&",
        ["job_card_state_code", "=", "127"],
        ["balance_amount_received_bool", "=", true],
      ];

      const jobCards = await this.orm.searchRead("project.task", domain, ["customer_city_id"]);
      const jobCardCityIdsSet = new Set();
      jobCards.forEach((card) => {
        if (card.customer_city_id && card.customer_city_id[0])
          jobCardCityIdsSet.add(Number(card.customer_city_id[0]));
      });

      const finalCityIds = Array.from(jobCardCityIdsSet);
      if (!finalCityIds.length) return;

      const cities = await this.orm.searchRead("res.city", [["id", "in", finalCityIds]], ["id", "name"]);
      this.state.cityList = cities;
      this.state.combinedCities = [
        ...this.state.cityList,
        ...(this.state.availableCities || []).filter((city) => !this.state.cityList.some((c) => c.id === city.id)),
      ];
    } catch (err) {
      this.state.cityList = [];
      this.state.combinedCities = [];
    }
  }

  async loadedJobcardStates() {
    if (!this.state.isPopulated) return;
    try {
      const work_center_ids = this.state.selectedWorkcenterId ? [parseInt(this.state.selectedWorkcenterId, 10)] : [];
      if (!work_center_ids.length) return;

      const domain = [
        ["work_center_id", "in", work_center_ids],
        "|",
        ["project_id", "=", this.state.project_id],
        "&",
        ["amc_project_id", "=", this.state.project_id],
        ["project_related_amc_bool", "=", true],
        "|",
        ["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES],
        "&",
        ["job_card_state_code", "=", "127"],
        ["balance_amount_received_bool", "=", true],
      ];

      const jobCards = await this.orm.searchRead("project.task", domain, [
        "job_card_state_code",
        "job_card_state",
        "balance_amount_received_bool",
      ]);

      if (!jobCards.length) {
        this.state.loadedJobcardStates = [];
        return;
      }

      const stateMap = new Map();
      jobCards.forEach((jc) => {
        if (!jc.job_card_state_code || !jc.job_card_state) return;
        if (ALLOWED_JOB_CARD_STATES.includes(jc.job_card_state_code)) {
          stateMap.set(jc.job_card_state_code, jc.job_card_state);
        }
        if (jc.job_card_state_code === "127" && jc.balance_amount_received_bool) {
          stateMap.set(jc.job_card_state_code, jc.job_card_state);
        }
      });

      this.state.loadedJobcardStates = Array.from(stateMap.entries()).map(([code, name]) => ({ id: code, name }));
    } catch (err) {
      this.state.loadedJobcardStates = [];
    }
  }

  async loadContracts() {
    if (!this.state.isPopulated) return;
    try {
      const domain = [
        ["contract_id", "!=", false],
        "|",
        ["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES],
        "&",
        ["job_card_state_code", "=", "127"],
        ["balance_amount_received_bool", "=", true],
      ];

      const tasks = await this.orm.searchRead("project.task", domain, [
        "id",
        "name",
        "contract_id",
        "user_ids",
        "work_center_id",
      ]);

      const contracts = [
        ...new Map(
          tasks
            .filter((t) => t.contract_id)
            .map((t) => [t.contract_id[0], { id: t.contract_id[0], name: t.contract_id[1] }])
        ).values(),
      ];

      this.state.contractList = contracts || [];
    } catch (error) {
      this.state.contractList = [];
    }
  }

  async onCityFilterChange(ev) {
    this.state.selectedCityId = ev.target.value || null;
    await this.loadJobCards();
  }

  async onStatusFilterChange(ev) {
    this.state.selectedStatusCode = ev.target.value || null;
    await this.loadJobCards();
  }

  async onContractFilterChange(ev) {
    this.state.selectedContractId = ev.target.value || null;
    await this.loadJobCards();
  }

  async loadUsers() {
    try {
      const users = await this.orm.searchRead(
        "res.users",
        [],
        ["id", "name", "property_warehouse_id", "warehouse_category_user_line_ids"],
      );
      this.userMap = Object.fromEntries(
        users.map((u) => [
          u.id,
          {
            name: u.name,
            property_warehouse_id: u.property_warehouse_id,
            warehouse_category_user_line_ids: u.warehouse_category_user_line_ids,
          },
        ]),
      );
    } catch (err) {
      console.error("Failed to load users:", err);
    }
  }

  async loadJobCards() {
    if (!this.state.isPopulated) {
      this.state.jobCards = [];
      return;
    }

    try {
      const wcId = this.state.selectedWorkcenterId ? parseInt(this.state.selectedWorkcenterId, 10) : null;
      if (!wcId) {
        this.state.jobCards = [];
        return;
      }

      // Base query: ONLY filtered by selected Work Center and valid workflow states
      // (Do NOT include technician_id or user_ids here)
      const domain = [
        ["work_center_id", "=", wcId],
        "|",
        ["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES],
        "&",
        ["job_card_state_code", "=", "127"],
        ["balance_amount_received_bool", "=", true],
      ];

      if (this.state.selectedCityId) {
        domain.push(["customer_city_id", "=", parseInt(this.state.selectedCityId, 10)]);
      }

      if (this.state.selectedStatusCode) {
        domain.push(["job_card_state_code", "=", this.state.selectedStatusCode]);
      }

      if (this.state.selectedContractId) {
        domain.push(["contract_id", "=", parseInt(this.state.selectedContractId, 10)]);
      }

      const jobCards = await this.orm.searchRead("project.task", domain, [
        "id",
        "name",
        "customer_name",
        "service_requested_datetime",
        "job_card_state_code",
        "job_state",
        "job_card_state",
        "customer_city_id",
        "country_district_id",
        "dealer_id",
        "project_id",
        "amc_project_id",
        "project_related_amc_bool",
        "used_location_equipment",
        "work_center_id",
        "contract_id",
        "partner_name",
      ]);

      // Filter tasks by active project selection (or user assigned projects)
      const pid = this.state.project_id;
      let finalJobCards = jobCards;

      if (pid) {
        finalJobCards = jobCards.filter((card) => {
          const taskProjectId = card.project_id?.[0] || null;
          const taskAmcId = card.amc_project_id?.[0] || null;
          return taskProjectId === pid || taskAmcId === pid;
        });
      } else if (this.state.userProjectIds && this.state.userProjectIds.length > 0) {
        finalJobCards = jobCards.filter((card) => {
          const taskProjectId = card.project_id?.[0] || null;
          const taskAmcId = card.amc_project_id?.[0] || null;
          return (
            (taskProjectId && this.state.userProjectIds.includes(taskProjectId)) ||
            (taskAmcId && this.state.userProjectIds.includes(taskAmcId))
          );
        });
      }

      const pad = (n) => n.toString().padStart(2, "0");

      this.state.jobCards = finalJobCards.map((card) => {
        const cityName = card.customer_city_id ? card.customer_city_id[1] : "";
        const districtName = card.country_district_id ? card.country_district_id[1] : "";
        const dealerId = card.dealer_id ? card.dealer_id[1] : "";

        let formattedDate = "";
        if (card.service_requested_datetime) {
          const d = new Date(card.service_requested_datetime.replace(" ", "T"));
          const localDate = new Date(d.getTime() + 3 * 60 * 60 * 1000);
          formattedDate = `${pad(localDate.getDate())}/${pad(localDate.getMonth() + 1)}/${localDate.getFullYear()} ${pad(localDate.getHours())}:${pad(localDate.getMinutes())}:${pad(localDate.getSeconds())}`;
        }

        return {
          ...card,
          customer_city_name: cityName,
          customer_district_name: districtName,
          service_requested_datetime_formatted: formattedDate,
          dealer_id: dealerId,
        };
      });
    } catch (err) {
      console.error("Error loading job cards:", err);
      this.state.jobCards = [];
    }
  }

  async onCardClick(ev) {
    ev.preventDefault();
    const id = parseInt(ev.currentTarget.dataset.id, 10);
    if (!id) return;
    this.state.selectedJobCardId = id;

    try {
      const jobCardData = await this.orm.searchRead(
        "project.task",
        [["id", "=", id]],
        [
          "id",
          "name",
          "customer_name",
          "service_requested_datetime",
          "job_card_state_code",
          "job_state",
          "job_card_state",
          "project_id",
          "amc_project_id",
          "project_related_amc_bool",
        ],
      );
      if (!jobCardData.length) return;
      this.env.bus.trigger("jobcard-selected", jobCardData[0]);
    } catch (err) {
      console.error("Error fetching job card:", err);
    }
  }

  async updateSelectedJobCard(data, isSlot = false) {
    if (!data) return;

    if (isSlot) {
      const plannedBegin = data.planned_date_begin ? new Date(data.planned_date_begin) : null;
      if (plannedBegin) plannedBegin.setHours(plannedBegin.getHours() + 3);

      const now = new Date();
      const truncateToMinute = (date) => {
        const d = new Date(date);
        d.setSeconds(0, 0);
        return d;
      };

      const planned = plannedBegin ? truncateToMinute(plannedBegin) : null;
      const current = truncateToMinute(now);

      if (planned && planned < current) {
        this.hasSlotClicked = false;
        return this.notification.add(
          "Scheduling Error: Jobcards cannot be assigned to past times.",
          { type: "danger" }
        );
      }

      this.state.planned_date_begin = data.planned_date_begin || null;
      this.state.planned_date_end = data.planned_date_end || null;
      this.state.user_ids = data.user_ids || [];
      const slotUserId = this.state.user_ids.length ? parseInt(this.state.user_ids[0], 10) : null;
      this.state.teamId = slotUserId || (this.state.selectedTechnicianId ? parseInt(this.state.selectedTechnicianId, 10) : null);
      if (!this.state.user_ids.length && this.state.teamId) {
        this.state.user_ids = [this.state.teamId];
      }
    } else {
      this.state.jobcardId = data.id;
      this.state.jobCardNumber = data.name || "";
      this.state.name = data.name || "";
      this.state.customerName = data.customer_name || "";
      this.state.serviceDatetime = data.service_requested_datetime || "";
      if (data.service_requested_datetime) {
        const d = new Date(data.service_requested_datetime.replace(" ", "T"));
        const pad = (n) => n.toString().padStart(2, "0");
        this.state.service_requested_datetime_formatted = `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours() + 3)}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
      } else {
        this.state.service_requested_datetime_formatted = "";
      }

      this.state.planned_date_begin = null;
      this.state.planned_date_end = null;
      this.state.user_ids = [];
      this.state.teamId = null;

      this.state.job_card_state_code = data.job_card_state_code;
      this.state.job_state = data.job_state;
      this.state.job_card_state = data.job_card_state;

      const stateCodeNum = parseInt(this.state.job_card_state_code, 10);
      if ([101, 107, 152, 156, 207, 117, 132, 122, 127].includes(stateCodeNum)) {
        return;
      }
    }

    if (this.state.teamId) {
      let user = this.userMap[this.state.teamId];
      if (!user || !user.warehouse_category_user_line_ids) {
        try {
          const userRecords = await this.orm.read(
            "res.users",
            [this.state.teamId],
            ["name", "property_warehouse_id", "warehouse_category_user_line_ids"],
          );
          if (userRecords.length) {
            user = {
              name: userRecords[0].name,
              property_warehouse_id: userRecords[0].property_warehouse_id,
              warehouse_category_user_line_ids: userRecords[0].warehouse_category_user_line_ids,
            };
            this.userMap[this.state.teamId] = user;
          }
        } catch (e) {
          console.error("Failed to read technician user details:", e);
        }
      }
      this.state.technicianName = user ? user.name : null;
      this.state.warehouseId = user ? user.property_warehouse_id : null;
      this.state.warehouseLineId = user ? user.warehouse_category_user_line_ids : null;
    } else {
      this.state.technicianName = null;
      this.state.warehouseId = null;
      this.state.warehouseLineId = null;
    }

    const warehouse = await this.workCenterlocationMatch();
    if (!warehouse) {
      this.hasSlotClicked = false;
      return;
    }

    try {
      await this.updateJobCard();
      await this.loadJobCards();
    } catch (err) {
      console.error(err);
    } finally {
      this.hasSlotClicked = false;
    }
  }

  async workCenterlocationMatch() {
    const stopFlow = (msg) => {
      this.hasSlotClicked = false;
      if (msg && this.notification) {
        this.notification.add(msg, { type: "info" });
      }
      return null;
    };

    this.hasSlotClicked = true;
    const taskId = this.state.selectedJobCardId;
    const task = await this._getTask(taskId);
    if (!task) return;

    const categoryId = task.product_category_id?.[0];
    const categoryName = task.product_category_id?.[1];
    const workCenterId = task.work_center_id?.[0] || null;

    let warehouse = null;
    let lineIds = this.state.warehouseLineId;
    let technicianRequired = false;

    if (workCenterId) {
      const workCenterLocation = await this.orm.searchRead(
        "work.center.location",
        [["id", "=", workCenterId]],
        ["technician_warehouse_required_bool"],
      );
      if (workCenterLocation.length) {
        technicianRequired = workCenterLocation[0].technician_warehouse_required_bool;
      }
    }

    if (technicianRequired === true) {
      if (!this.state.teamId) {
        this.dialog.add(ConfirmationDialog, {
          title: _t("Validation Error"),
          body: markup(_t("Please select a technician or click on a technician's row to schedule this job card.")),
        });
        return;
      }

      if (lineIds && lineIds.length) {
        const lines = await this.orm.searchRead(
          "res.users.line",
          [["id", "in", lineIds], ["product_category_line_id", "=", categoryId]],
          ["warehouse_line_id"],
        );
        if (lines.length && lines[0].warehouse_line_id) {
          warehouse = lines[0].warehouse_line_id[0];
        }
      }

      if (!workCenterId) return stopFlow("Work Center is not configured for this Job Card.");

      let warehousedata = await this.orm.searchRead(
        "stock.warehouse",
        [
          ["id", "=", warehouse],
          ["product_category_ids", "in", [categoryId]],
          ["warehouse_type", "=", "technician_warehouse"],
        ],
        ["id", "name", "warehouse_type"],
      );
      warehouse = warehousedata?.[0]?.id;
    } else {
      if (!warehouse) {
        if (!workCenterId) return stopFlow("Work Center is not configured for this Job Card.");

        let warehousedata = await this.orm.searchRead(
          "stock.warehouse",
          [
            ["work_center_ids", "=", workCenterId],
            ["region_default_warehouse_bool", "=", true],
            ["product_category_ids", "in", [categoryId]],
            ["warehouse_type", "=", "main_warehouse"],
          ],
          ["id", "name", "warehouse_type"],
        );
        warehouse = warehousedata?.[0]?.id;
      }
    }

    if (!warehouse) {
      let message = technicianRequired
        ? markup(_t("Technician warehouse is not available for technician <b>%s</b> for category <b>%s</b>.", this.state.technicianName || _t("Unassigned"), categoryName))
        : markup(_t("Main warehouse is not available for category <b>%s</b>.", categoryName));

      this.dialog.add(ConfirmationDialog, {
        title: _t("Validation Error"),
        body: message,
      });
      return;
    }

    this.matchedWarehouseId = warehouse;
    this.hasSlotClicked = false;
    return warehouse;
  }

  async _getTask(taskId) {
    const [task] = await this.orm.searchRead(
      "project.task",
      [["id", "=", taskId]],
      ["work_center_id", "product_category_id"],
    );
    return task;
  }

  async updateJobCard() {
    if (!this.state.jobcardId) return;

    try {
      const taskData = await this.orm.searchRead(
        "project.task",
        [["id", "=", this.state.jobcardId]],
        [
          "second_visit_technician_bool",
          "job_card_state_code",
          "technician_id",
          "unit_pull_out_status_check",
          "service_warranty_id",
          "balance_amount_received_bool",
          "last_rescheduled_status_code",
        ],
      );

      if (!taskData.length) return;

      const task = taskData[0];
      if (task.service_warranty_id?.length) {
        const warrantyId = task.service_warranty_id[0];
        const warrantyData = await this.orm.read("service.warranty", [warrantyId], ["warranty_applicable_bool"]);
        task.warranty_applicable_bool = warrantyData.length && warrantyData[0].warranty_applicable_bool === false ? false : true;
      } else {
        task.warranty_applicable_bool = false;
      }

      let stateCode = parseInt(task.job_card_state_code, 10);
      const isUnitPullOutStatusCheck = task.unit_pull_out_status_check;
      const balanceAmountreceivedBool = task.balance_amount_received_bool;
      const warrantyApplicablebool = task.warranty_applicable_bool;
      const isSecondVisit = task.second_visit_technician_bool;
      let lastRescheduledStatusCode = "";
      let effectiveStateCode = "";

      if (warrantyApplicablebool === false && stateCode === 127 && isUnitPullOutStatusCheck === true && balanceAmountreceivedBool === true) {
        const forcedStage = await this.orm.searchRead("project.task.type", [["code", "=", "204"]], ["id", "code", "name"]);
        if (forcedStage.length) {
          this.state.job_card_state_code = parseInt(forcedStage[0].code, 10);
          this.state.job_state = forcedStage[0].id;
          this.state.job_card_state = forcedStage[0].name;
        }
      } else if (stateCode === 107 && task.last_rescheduled_status_code) {
        effectiveStateCode = task.last_rescheduled_status_code;
        const stageLastResult = await this.orm.searchRead("project.task.type", [["code", "=", effectiveStateCode]], ["id", "code", "name", "dynamic_job_state_code"]);
        if (stageLastResult.length) {
          this.state.job_card_state_code = parseInt(stageLastResult[0].code, 10);
          this.state.job_state = stageLastResult[0].id;
          this.state.job_card_state = stageLastResult[0].name;
          lastRescheduledStatusCode = effectiveStateCode;
        }
      } else {
        const stageResult = await this.orm.searchRead("project.task.type", [["code", "=", stateCode]], ["id", "code", "name", "dynamic_job_state_code"]);
        const stageState = await this.orm.searchRead("project.task.type", [["code", "=", stageResult[0].dynamic_job_state_code]], ["id", "code", "name", "scheduling_status_bool"]);

        this.state.job_card_state_code = parseInt(stageResult[0].dynamic_job_state_code, 10);
        this.state.job_state = stageState[0].id;
        this.state.job_card_state = stageState[0].name;
        lastRescheduledStatusCode = task.last_rescheduled_status_code || "";
        if (stageState.length && stageState[0].scheduling_status_bool === true) {
          lastRescheduledStatusCode = stageState[0].code || "";
        }
      }

      const values = {
        planned_date_begin: this.state.planned_date_begin,
        planned_date_end: this.state.planned_date_end,
        job_card_state_code: this.state.job_card_state_code,
        job_state: this.state.job_state,
        job_card_state: this.state.job_card_state,
        technician_id: this.state.teamId || null,
        warehouse_id: this.matchedWarehouseId || 181,
        last_rescheduled_status_code: lastRescheduledStatusCode || "",
      };

      if (isSecondVisit && (stateCode === 132 || stateCode === 122)) {
        values.technician_second_visit_id = this.state.teamId;
      } else if (stateCode !== 117) {
        values.technician_first_visit_id = this.state.teamId;
      }

      if (Array.isArray(values.job_state)) {
        values.job_state = null;
      }

      Object.keys(values).forEach((key) => {
        if (values[key] === undefined) delete values[key];
      });

      await this.orm.write("project.task", [this.state.jobcardId], values);
      await this.updateMachineRepairSupport(this.state.jobcardId, values);
      this.resetState();
    } catch (err) {
      console.error("Failed to update job card:", err);
    }
  }

  resetState() {
    this.state.showTable = false;
    this.state.jobCards = [];
    this.state.jobcardId = null;
    this.state.jobCardNumber = "";
    this.state.name = "";
    this.state.customerName = "";
    this.state.serviceDatetime = "";
    this.state.planned_date_begin = null;
    this.state.planned_date_end = null;
    this.state.user_ids = [];
    this.state.teamId = null;
    this.state.technicianName = null;
    this.state.job_card_state_code = null;
    this.state.job_state = null;
    this.state.job_card_state = "";
    this.state.service_requested_datetime_formatted = "";
    this.state.selectedJobCardId = "";
  }

  async updateMachineRepairSupport(jobcardId, values) {
    const mrsRecords = await this.orm.searchRead("machine.repair.support", [["task_id", "=", jobcardId]], ["id"]);
    if (!mrsRecords.length) return;

    const taskData = await this.orm.read("project.task", [jobcardId], [
      "team_id",
      "technician_id",
      "planned_date_begin",
      "job_card_state",
      "job_card_state_code",
    ]);
    const taskTeamId = taskData?.[0]?.team_id?.[0] || null;
    const plannedDateBegin = taskData?.[0]?.planned_date_begin || null;
    const taskjobstate = values.job_card_state || null;
    const taskjobcardstatecode = taskData?.[0]?.job_card_state_code || null;
    const technicianId = Array.isArray(taskData?.[0]?.technician_id) ? taskData[0].technician_id[0] : null;

    const valuesMRS = {
      task_id: jobcardId,
      service_request_state: taskjobstate || null,
      service_request_state_code: taskjobcardstatecode || null,
      user_id: technicianId || null,
      team_id: taskTeamId || null,
      call_request_appointment_date: this.state.serviceDatetime || null,
      technician_appointment_date: plannedDateBegin || null,
    };

    const mrsIds = mrsRecords.map((r) => r.id).filter((id) => !isNaN(id));
    if (mrsIds.length) {
      try {
        await this.orm.write("machine.repair.support", mrsIds, valuesMRS);
      } catch (err) {
        console.error("Failed to update MRS:", err);
      }
    }

    setTimeout(() => {
      document.querySelectorAll(".oi.oi-arrow-right").forEach((el) => el.click());
      document.querySelectorAll(".oi.oi-arrow-left").forEach((el) => el.click());
    }, 2000);
  }

  attachHighlightHandler() {
    const container = document.querySelector(".o_gantt_view, .o_gantt, .o_content, .o_view_controller");
    if (!container || container.dataset.highlightAttached) return;

    container.addEventListener("click", (ev) => this.handleSlotClick(ev));
    container.dataset.highlightAttached = "true";
  }

  handleSlotClick(ev) {
    const cell = ev.target.closest("td[data-resource-id][data-date], td[data-date], .o_gantt_cell[data-date]");
    if (!cell) return;

    const oldLabel = cell.querySelector(".jobcard-label");
    if (oldLabel) oldLabel.remove();

    const cellRect = cell.getBoundingClientRect();
    const relTop = ev.clientY - cellRect.top;
    const relLeft = ev.clientX - cellRect.left;

    const label = document.createElement("div");
    label.className = "jobcard-label";
    Object.assign(label.style, {
      position: "absolute",
      top: relTop + "px",
      left: relLeft + "px",
      borderRadius: "6px",
      background: "rgba(255, 235, 59, 0.55)",
      outline: "2px solid rgba(255, 193, 7, 0.9)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "#2c3e50",
      fontWeight: "bold",
      fontSize: "11px",
      padding: "4px 6px",
      zIndex: "1",
      width: "100px",
      height: "25px",
    });

    cell.style.position = "relative";
    label.textContent = this.state.name || `Jobcard ${this.state.jobcardId}`;
    cell.appendChild(label);
    setTimeout(() => label.remove(), 2000);
  }
}

registry.category("components").add("JobcardList", JobcardList);