/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { FilterDialog } from "./filter_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";
const ALLOWED_JOB_CARD_STATES = [
  "101", // New
  "107", // Rescheduled (Collect the re-schedule date & time @ the time of this request)
  "117", // Unit Pull Out
  "132", //"Unit Ready For Delivery"
  "122", //Parts Ready & Rescheduled,
  "152",
  "156",
  "207",
];

export class JobcardList extends Component {
  static template = "JobcardList";

  setup() {
    this.orm = useService("orm");
    this.notification = useService("notification");
    this.actionService = useService("action");
    this.dialog = useService("dialog");
    const context = this.env.context || {};
    this.hideJobCardList = context.hide_jobcard_list || false;

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
      selectedWorkcenterId: null,
      contractList: [],
      selectedContractId: null,
      project_related_amc_bool: false,
      isAmcProject: false,
      project_id: null,
    });

    this.userMap = {};
    this.hasSlotClicked = false;
    this.cardListRef = useRef("cardList");
    this.isRTL = session.user_context.lang.startsWith("ar");

    onMounted(async () => {
      if (this.cardListRef.el) {
        this.cardListRef.el.style.direction = this.isRTL ? "rtl" : "ltr";
      }
      await this.loadUsers();
      await this.loadJobCards();
      await this.loadCities();
      await this.loadedJobcardStates();
      // await this.loadWorkCenters();
      await this.loadContracts();
      this.attachHighlightHandler();
    });

    onWillStart(async () => {
      const user_workcenter = await this.orm.searchRead(
        "res.users",
        [["id", "=", session.user_id]],
        ["default_work_center_id"],
      );
      console.log("user_workcenter", user_workcenter);

      const work_center_id = user_workcenter[0].default_work_center_id?.[0];
      if (!work_center_id) return;

      const user_workcenter_city = await this.orm.searchRead(
        "res.city",
        [["def_work_center_id", "=", work_center_id]],
        ["name", "def_work_center_id"],
      );
      console.log("res.city", user_workcenter_city);
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
        await this.loadJobCards();
        await new Promise((resolve) => setTimeout(resolve, 2000));
      });
      useBus(this.env.bus, "project-filter-updated", async (payload) => {
        console.log("📥 Project filter received:", payload);
        const projectId = payload?.detail?.project_id || false;
        console.log("📌 Updated this.state.project_id:", projectId);
        this.state.project_id = projectId;

        // await this.loadContracts();

        // await this.loadContracts();
        await this.loadJobCards();
        await this.loadedJobcardStates(); // 👈 ADD THIS
      });
    }
  }
  get isAmcProject() {
    return this.state.project_id === 4;
  }
  resetSelectedJobCard() {
    this.state.selectedJobCardId = null;
    this.state.name = "";
    this.state.customerName = "";
    this.state.service_requested_datetime_formatted = "";
  }

  async openFilterDialog() {
    try {
      if (!this.state.combinedCities.length) {
        await this.loadCities();
      }
      if (!this.state.loadedJobcardStates?.length) {
        await this.loadJobcardStates();
      }

      // Open dialog
      this.dialog.add(FilterDialog, {
        title: "Filter Job Cards",
        cityList: this.state.combinedCities,
        jobStates: this.state.loadedJobcardStates,
        onApply: (filters) => this.applyFilter(filters),
      });
    } catch (error) {
      console.error("❌ Error opening filter dialog:", error);
      this.notification.add("Failed to open filter dialog. Please try again.", {
        type: "danger",
      });
    }
  }

  async applyFilter(filters) {
    try {
      console.log("✅ Filters received:", filters);

      const domain = [["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES]];

      if (filters.city && !isNaN(parseInt(filters.city))) {
        domain.push(["customer_city_id", "=", parseInt(filters.city)]);
      }

      if (filters.status && !isNaN(parseInt(filters.status))) {
        domain.push(["job_card_state_id", "=", parseInt(filters.status)]);
      }

      console.log("🔍 Final Domain:", domain);

      const test = await this.orm.searchRead("project.task", [], ["id"], {
        limit: 1,
      });

      const jobCards = await this.orm.searchRead("project.task", domain, [
        "name",
        "customer_city_id",
        "job_card_state_id",
      ]);

      this.state.jobCards = jobCards;

      if (!jobCards.length) {
        this.notification.add("No job cards found for the selected filters.", {
          type: "info",
        });
      } else {
        this.notification.add(
          `✅ ${jobCards.length} job cards loaded successfully.`,
          { type: "success" },
        );
      }
    } catch (error) {
      this.notification.add("Failed to apply filters. Please try again.", {
        type: "danger",
      });
    }
  }

  // async loadWorkCenters() {
  //   // may 28/2026
  //   try {
  //     const workCenters = await this.orm.searchRead(
  //       "work.center.location",
  //       [],
  //       ["id", "name"],
  //     );

  //     this.state.workCenterList = workCenters || [];
  //     console.log("this.state.workCenterList", this.state.workCenterList);
  //   } catch (err) {
  //     this.state.workCenterList = [];
  //     console.error("Error loading work centers:", err);
  //   }
  // }

  async loadCities() {
    try {
      const users = await this.orm.searchRead(
        "res.users",
        [["id", "=", session.user_id]],
        ["default_work_center_id"],
      );

      const work_center_ids = (users[0]?.default_work_center_id || []).map(
        (wc) => (Array.isArray(wc) ? wc[0] : wc),
      );

      if (!work_center_ids.length) {
        this.state.cityList = [];
        this.state.combinedCities = [];
        return;
      }

      const cityRecords = await this.orm.searchRead(
        "res.city",
        [["def_work_center_id", "in", work_center_ids]],
        ["id", "name"],
      );

      const allCityIds = cityRecords.map((c) => Number(c.id));
      if (!allCityIds.length) {
        this.state.cityList = [];
        this.state.combinedCities = [];
        return;
      }

      // const domain = [
      //   ["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES],
      //   ["customer_city_id", "in", allCityIds],
      // ];
      // Added on Vengatesh - mar-21-2026
      const domain = [
        "&",
        ["customer_city_id", "in", allCityIds],
        // Added on Vengatesh - mar-23-2026 amc_project_id ,project_related_amc_bool
        // "&",
        // ["amc_project_id", "=", this.state.project_id],
        "&",
        ["project_related_amc_bool", "=", true],
        "|",
        ["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES],
        "&",
        ["job_card_state_code", "=", "127"],
        ["balance_amount_received_bool", "=", true],
      ];

      const jobCards = await this.orm.searchRead("project.task", domain, [
        "customer_city_id",
      ]);

      const jobCardCityIdsSet = new Set();
      jobCards.forEach((card) => {
        if (card.customer_city_id && card.customer_city_id[0])
          jobCardCityIdsSet.add(Number(card.customer_city_id[0]));
      });

      const finalCityIds = Array.from(jobCardCityIdsSet);
      if (!finalCityIds.length) {
        this.state.cityList = [];
        this.state.combinedCities = [];
        return;
      }

      const cities = await this.orm.searchRead(
        "res.city",
        [["id", "in", finalCityIds]],
        ["id", "name"],
      );

      this.state.cityList = cities;

      this.state.combinedCities = [
        ...this.state.cityList,
        ...(this.state.availableCities || []).filter(
          (city) => !this.state.cityList.some((c) => c.id === city.id),
        ),
      ];
    } catch (err) {
      this.state.cityList = [];
      this.state.combinedCities = [];
    }
  }
  async loadedJobcardStates() {
    try {
      const users = await this.orm.searchRead(
        "res.users",
        [["id", "=", session.user_id]],
        ["default_work_center_id"],
      );

      const work_center_ids = (users[0]?.default_work_center_id || []).map(
        (wc) => (Array.isArray(wc) ? wc[0] : wc),
      );

      if (!work_center_ids.length) {
        console.warn("Current user has no default work center.");
        this.state.loadedJobcardStates = [];
        return;
      }

      // const domain = [
      //   ["work_center_id", "in", work_center_ids],
      //   ["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES],
      // ];

      // // Added on Vengatesh - mar-21-2026
      // const domain = [
      //   "&",
      //   ["work_center_id", "in", work_center_ids],
      //   // Added on Vengatesh - mar-23-2026 amc_project_id ,project_related_amc_bool
      //   "&",
      //   // ["amc_project_id", "=", this.state.project_id],
      //   // "&",
      //   // ["project_related_amc_bool", "=", true],
      //   // "|",
      //   ["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES],
      //   "&",
      //   ["job_card_state_code", "=", "127"],
      //   ["balance_amount_received_bool", "=", true],
      // ];
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
      console.log("jobCards", jobCards);

      if (!jobCards.length) {
        this.state.loadedJobcardStates = [];
        return;
      }

      // const stateMap = new Map();
      // jobCards.forEach((jc) => {
      //   if (jc.job_card_state_code && jc.job_card_state) {
      //     stateMap.set(jc.job_card_state_code, jc.job_card_state);
      //   }
      // });

      // const filteredStates = Array.from(stateMap.entries())
      //   .filter(([code]) => ALLOWED_JOB_CARD_STATES.includes(code))
      //   .map(([code, name]) => ({
      //     id: code,
      //     name,
      //   }));

      // this.state.loadedJobcardStates = filteredStates;

      // console.log(
      //   "this.state.loadedJobcardStates",
      //   this.state.loadedJobcardStates,
      // );

      // Added on Vengatesh - mar-21-2026
      const stateMap = new Map();
      jobCards.forEach((jc) => {
        if (!jc.job_card_state_code || !jc.job_card_state) return;

        // Include normal allowed states
        if (ALLOWED_JOB_CARD_STATES.includes(jc.job_card_state_code)) {
          stateMap.set(jc.job_card_state_code, jc.job_card_state);
        }

        // Include state "127" only if balance received
        if (
          jc.job_card_state_code === "127" &&
          jc.balance_amount_received_bool
        ) {
          stateMap.set(jc.job_card_state_code, jc.job_card_state);
        }
      });

      this.state.loadedJobcardStates = Array.from(stateMap.entries()).map(
        ([code, name]) => ({ id: code, name }),
      );

      console.log("Loaded job card states:", this.state.loadedJobcardStates);
    } catch (err) {
      this.state.loadedJobcardStates = [];
    }
  }
  // async loadContracts() {
  //   try {
  //     // ---------------------------------------------------
  //     // DOMAIN (JOB CARDS SOURCE)
  //     // ---------------------------------------------------
  //     const domain = [
  //       ["contract_id", "!=", false],

  //       "|",
  //       ["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES],
  //       "&",
  //       ["job_card_state_code", "=", "127"],
  //       ["balance_amount_received_bool", "=", true],
  //     ];

  //     console.log("DOMAIN:", domain);

  //     // ---------------------------------------------------
  //     // LOAD TASKS
  //     // ---------------------------------------------------
  //     const tasks = await this.orm.searchRead(
  //       "project.task",
  //       domain,
  //       ["contract_id", "work_center_id"],
  //       // {
  //       //   limit: 500,
  //       //   order: "id desc",
  //       // },
  //     );

  //     console.log("TASKS:", tasks);

  //     // ---------------------------------------------------
  //     // UNIQUE CONTRACT IDS
  //     // ---------------------------------------------------
  //     const contractIds = [
  //       ...new Set(
  //         tasks.map((t) => t.contract_id && t.contract_id[0]).filter(Boolean),
  //       ),
  //     ];

  //     console.log("CONTRACT IDS:", contractIds);
  //     // console.log("workCenterIds", workCenterIds);

  //     // ---------------------------------------------------
  //     // NO CONTRACTS
  //     // ---------------------------------------------------
  //     if (!contractIds.length) {
  //       this.state.contractList = [];
  //       return;
  //     }

  //     // ---------------------------------------------------
  //     // LOAD CONTRACTS (CORRECT MODEL)
  //     // ---------------------------------------------------
  //     const contracts = await this.orm.searchRead(
  //       "subscription.contracts", // ✅ FIXED
  //       [["id", "in", contractIds]],

  //       ["id", "name", "work_center_id"],
  //     );
  //     console.log("contracts", contracts);
  //     const workCenters = [
  //       ...new Set(contracts.map((c) => c.work_center_id?.[0]).filter(Boolean)),
  //     ];
  //     console.log("contractWorkcenters", workCenters);
  //     const contractWorkcenters = await this.orm.searchRead(
  //       "work.center.location",
  //       [["id", "in", workCenters]],
  //       ["id", "name"],
  //     );
  //     console.log("contractWorkcenters", contractWorkcenters);

  //     this.state.contractList = contracts || [];
  //     this.state.workCenterList = contractWorkcenters || [];
  //   } catch (err) {
  //     console.error("ERROR LOAD CONTRACTS:", err);
  //     this.state.contractList = [];
  //     this.state.workCenterList;
  //   }
  // }
  async loadContracts() {
    try {
      // const tasks = await this.orm.searchRead(
      //   "project.task",
      //   [],
      //   ["id", "name", "user_ids", "contract_id"],
      //   { limit: 20 },
      // );

      // console.log("VISIBLE TASKS:", tasks);
      // ---------------------------------------------------
      // JOB CARD DOMAIN
      // ---------------------------------------------------
      const domain = [
        ["contract_id", "!=", false],
        "|",
        ["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES],
        "&",
        ["job_card_state_code", "=", "127"],
        ["balance_amount_received_bool", "=", true],
      ];

      console.log("Contract Load Domain:", domain);

      // ---------------------------------------------------
      // LOAD TASKS
      // ---------------------------------------------------
      const tasks = await this.orm.searchRead("project.task", domain, [
        "id",
        "name",
        "contract_id",
        "user_ids",
        "work_center_id",
      ]);

      console.log("Loaded Tasks:", tasks);

      // ---------------------------------------------------
      // GET UNIQUE CONTRACT IDS
      // ---------------------------------------------------
      const contractIds = [
        ...new Set(tasks.map((task) => task.contract_id?.[0]).filter(Boolean)),
      ];

      console.log("Contract IDs:", contractIds);

      if (!contractIds.length) {
        this.state.contractList = [];
        this.state.workCenterList = [];
        return;
      }

      // ---------------------------------------------------
      // LOAD CONTRACTS
      // ---------------------------------------------------
      // const contracts = await this.orm.searchRead(
      //   "subscription.contracts",
      //   [["id", "in", contractIds]],
      //   ["id", "name", "work_center_id"],
      // );

      // console.log("Loaded Contracts:", contracts);
      // Build contract list from task data
      const contracts = [
        ...new Map(
          tasks
            .filter((t) => t.contract_id)
            .map((t) => [
              t.contract_id[0],
              {
                id: t.contract_id[0],
                name: t.contract_id[1],
              },
            ]),
        ).values(),
      ];

      console.log("Contracts From Tasks:", contracts);

      // ---------------------------------------------------
      // GET UNIQUE WORK CENTER IDS
      // ---------------------------------------------------
      // const workCenterIds = [
      //   ...new Set(
      //     contracts
      //       .map((contract) => contract.work_center_id?.[0])
      //       .filter(Boolean),
      //   ),
      // ];
      const workCenters = [
        ...new Map(
          tasks
            .filter((t) => t.work_center_id)
            .map((t) => [
              t.work_center_id[0],
              {
                id: t.work_center_id[0],
                name: t.work_center_id[1],
              },
            ]),
        ).values(),
      ];

      console.log("Work Center IDs:", workCenters);

      // let workCenters = [];

      // if (workCenterIds.length) {
      //   workCenters = await this.orm.searchRead(
      //     "work.center.location",
      //     [["id", "in", workCenterIds]],
      //     ["id", "name"],
      //   );
      // }

      console.log("Loaded Work Centers:", workCenters);

      // ---------------------------------------------------
      // UPDATE STATE
      // ---------------------------------------------------
      this.state.contractList = contracts || [];
      this.state.workCenterList = workCenters || [];

      console.log("Final Contract List:", this.state.contractList);
      console.log("Final Work Center List:", this.state.workCenterList);
    } catch (error) {
      console.error("Error Loading Contracts:", error);

      this.state.contractList = [];
      this.state.workCenterList = [];
    }
  }

  async onCityFilterChange(ev) {
    const cityId = ev.target.value || null;
    this.state.selectedCityId = cityId;

    await this.loadJobCards();
  }
  async onStatusFilterChange(ev) {
    const statusCode = ev.target.value || null;
    this.state.selectedStatusCode = statusCode;

    await this.loadJobCards();
  }
  async onWorkcenterFilterChange(ev) {
    // May 28 2026
    const wprkcenterId = ev.target.value || null;
    this.state.selectedWorkcenterId = wprkcenterId;

    await this.loadJobCards();
  }
  async onContractFilterChange(ev) {
    const contractId = ev.target.value || null;

    this.state.selectedContractId = contractId;

    await this.loadJobCards();
  }

  // async loadUsers() {
  //   try {
  //     const users = await this.orm.searchRead("res.users", [], ["id", "name"]);
  //     this.userMap = Object.fromEntries(users.map((u) => [u.id, u.name]));
  //   } catch (err) {
  //     console.error("❌ Failed to load users:", err);
  //   }
  // }
  // Added on Vengatesh - mar-21-2026
  async loadUsers() {
    try {
      const users = await this.orm.searchRead(
        "res.users",
        [],
        [
          "id",
          "name",
          "property_warehouse_id",
          "warehouse_category_user_line_ids",
        ],
      );
      // this.userMap = Object.fromEntries(users.map((u) => [u.id, u.name]));
      this.userMap = Object.fromEntries(
        users.map((u) => [
          u.id, // The Key
          {
            // The Value (an object)
            name: u.name,
            property_warehouse_id: u.property_warehouse_id,
            warehouse_category_user_line_ids:
              u.warehouse_category_user_line_ids,
          },
        ]),
      );
    } catch (err) {
      console.error("❌ Failed to load users:", err);
    }
  }

  async loadJobCards() {
    try {
      // ---------------------------------------------------------
      // 1. Load user WC
      // ---------------------------------------------------------
      const user = await this.orm.searchRead(
        "res.users",
        [["id", "=", session.user_id]],
        ["default_work_center_id"],
      );

      const work_center_ids = (user[0]?.default_work_center_id || []).map(
        (wc) => (Array.isArray(wc) ? wc[0] : wc),
      );

      if (!work_center_ids.length) {
        this.state.jobCards = [];
        this.state.cityList = [];
        return;
      }

      // ---------------------------------------------------------
      // 2. Load allowed cities based on WC
      // ---------------------------------------------------------
      const cityRecords = await this.orm.searchRead(
        "res.city",
        [["def_work_center_id", "in", work_center_ids]],
        ["id", "name"],
      );
      const allCityIds = cityRecords.map((c) => c.id);

      // ---------------------------------------------------------
      // 3. Base domain
      // ---------------------------------------------------------
      // const domain = [["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES]];

      // Added on Vengatesh - mar-21-2026
      const domain = [
        // "&",
        // ["contract_id", "!=", false],
        "|",
        ["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES],
        "&",
        ["job_card_state_code", "=", "127"],
        ["balance_amount_received_bool", "=", true],
      ];

      if (allCityIds.length) {
        domain.push(["customer_city_id", "in", allCityIds]);
      }

      if (this.state.selectedCityId) {
        domain.push([
          "customer_city_id",
          "=",
          parseInt(this.state.selectedCityId),
        ]);
      }

      if (this.state.selectedStatusCode) {
        domain.push([
          "job_card_state_code",
          "=",
          this.state.selectedStatusCode,
        ]);
      }

      if (this.state.selectedWorkcenterId) {
        domain.push([
          "work_center_id",
          "=",
          parseInt(this.state.selectedWorkcenterId),
        ]);
      }
      if (this.state.selectedContractId) {
        domain.push([
          "contract_id",
          "=",
          parseInt(this.state.selectedContractId),
        ]);
      }

      // ---------------------------------------------------------
      // 4. Get base jobCards (no project filter yet)
      // ---------------------------------------------------------
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
      ]);

      console.log("jobCards (Base):", jobCards);

      // ---------------------------------------------------------
      // 5. Apply project/amc filter
      // ---------------------------------------------------------
      const pid = this.state.project_id;
      let finalJobCards = jobCards;
      if (pid) {
        finalJobCards = jobCards.filter((card) => {
          const projectId = card.project_id?.[0] || null;
          const amcId = card.amc_project_id?.[0] || null;

          // NORMAL PROJECT
          const isNormalMatch = pid === projectId && amcId === projectId;

          // AMC PROJECT (project_id must NOT be null + amc_project_id must match pid)
          const isAmcMatch = projectId !== null && amcId === pid;

          return isNormalMatch || isAmcMatch;
        });
      }
      // // ---------------------------------------------------------
      // // 5. Apply project/amc filter
      // // ---------------------------------------------------------
      // const pid = this.state.project_id;
      // let finalJobCards = jobCards;

      // if (pid) {
      //   finalJobCards = jobCards.filter((card) => {
      //     const projectId = card.project_id?.[0] || null;

      //     const amcId = card.amc_project_id?.[0] || null;

      //     const isAmcBool = card.project_related_amc_bool || false;

      //     // -------------------------------------------------
      //     // NORMAL PROJECT
      //     // Example:
      //     // project_id = HHS
      //     // -------------------------------------------------
      //     const isNormalMatch =
      //       (projectId === pid) === amcId && isAmcBool === false;

      //     // -------------------------------------------------
      //     // AMC PROJECT
      //     // Example:
      //     // project_id = HHS AMC Project
      //     // amc_project_id = HHS
      //     // project_related_amc_bool = true
      //     // -------------------------------------------------
      //     const isAmcMatch = isAmcBool && amcId === pid;

      //     return isNormalMatch || isAmcMatch;
      //   });
      // }

      // console.log("✔ Filtered jobCards:", finalJobCards);

      // ---------------------------------------------------------
      // 6. Map values (apply to FILTERED LIST)
      // ---------------------------------------------------------
      const pad = (n) => n.toString().padStart(2, "0");

      this.state.jobCards = finalJobCards.map((card) => {
        const cityName = card.customer_city_id ? card.customer_city_id[1] : "";
        const districtName = card.country_district_id
          ? card.country_district_id[1]
          : "";
        const dealerId = card.dealer_id ? card.dealer_id[1] : "";

        let formattedDate = "";
        if (card.service_requested_datetime) {
          const d = new Date(card.service_requested_datetime.replace(" ", "T"));
          const localDate = new Date(d.getTime() + 3 * 60 * 60 * 1000); // +3h
          formattedDate = `${pad(localDate.getDate())}/${pad(
            localDate.getMonth() + 1,
          )}/${localDate.getFullYear()} ${pad(localDate.getHours())}:${pad(
            localDate.getMinutes(),
          )}:${pad(localDate.getSeconds())}`;
        }

        return {
          ...card,
          customer_city_name: cityName,
          customer_district_name: districtName,
          service_requested_datetime_formatted: formattedDate,
          dealer_id: dealerId,
        };
      });

      // ---------------------------------------------------------
      // 7. Build City List
      // ---------------------------------------------------------
      const citySet = new Set();
      this.state.jobCards.forEach((card) => {
        if (card.customer_city_id && card.customer_city_id[0])
          citySet.add(Number(card.customer_city_id[0]));
      });

      const filteredCityIds = Array.from(citySet);
      this.state.cityList = cityRecords.filter((c) =>
        filteredCityIds.includes(Number(c.id)),
      );
    } catch (err) {
      this.state.jobCards = [];
      this.state.cityList = [];
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
      console.log("jobCardData", jobCardData);
      if (!jobCardData.length) return;
      this.env.bus.trigger("jobcard-selected", jobCardData[0]);
    } catch (err) {
      console.error("❌ Error fetching job card:", err);
    }
  }

  async updateSelectedJobCard(data, isSlot = false) {
    if (!data) return;

    if (isSlot) {
      const plannedBegin = data.planned_date_begin
        ? new Date(data.planned_date_begin)
        : null;
      if (plannedBegin) {
        plannedBegin.setHours(plannedBegin.getHours() + 3);
      }

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
          "Scheduling Error: Jobcards cannot be assigned to past times. Please select the current or a future time.",
          {
            type: "danger",
          },
        );
      }

      this.state.planned_date_begin = data.planned_date_begin || null;
      this.state.planned_date_end = data.planned_date_end || null;
      this.state.user_ids = data.user_ids || [];
      this.state.teamId = this.state.user_ids.length
        ? parseInt(this.state.user_ids[0], 10)
        : null;
    } else {
      this.state.jobcardId = data.id;
      this.state.jobCardNumber = data.name || "";
      this.state.name = data.name || "";
      this.state.customerName = data.customer_name || "";
      this.state.serviceDatetime = data.service_requested_datetime || "";
      if (data.service_requested_datetime) {
        const d = new Date(data.service_requested_datetime.replace(" ", "T"));
        const pad = (n) => n.toString().padStart(2, "0");
        this.state.service_requested_datetime_formatted = `${pad(
          d.getDate(),
        )}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(
          d.getHours() + 3,
        )}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
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

      if (
        parseInt(this.state.job_card_state_code, 10) === 101 ||
        parseInt(this.state.job_card_state_code, 10) === 107 ||
        parseInt(this.state.job_card_state_code, 10) === 152 ||
        parseInt(this.state.job_card_state_code, 10) === 156 ||
        parseInt(this.state.job_card_state_code, 10) === 207
      ) {
        return;
        // comment by
        // Added on Vengatesh - mar-21-2026
        // this.state.job_card_state_code = 102;
        // this.state.job_state = 1132;
        // this.state.job_card_state = "Scheduled";
      } else if (parseInt(this.state.job_card_state_code, 10) === 117) {
        return;
      } else if (parseInt(this.state.job_card_state_code, 10) === 132) {
        return;
      } else if (parseInt(this.state.job_card_state_code, 10) === 122) {
        return;
      } else if (parseInt(this.state.job_card_state_code, 10) === 127) {
        // Added on Vengatesh - mar-21-2026
        return;
      }
    }

    // this.state.technicianName = this.userMap[this.state.teamId] || null;
    // Added on Vengatesh - mar-21-2026
    const user = this.userMap[this.state.teamId];
    this.state.technicianName = user ? user.name : null;
    this.state.warehouseId = user ? user.property_warehouse_id : null;
    console.log(
      " this.state.warehouseId",
      this.state.warehouseId,
      this.state.technicianName,
    );
    this.state.warehouseLineId = user
      ? user.warehouse_category_user_line_ids
      : null;

    let jobcardAmcId = this.state.project_id;
    console.log("jobcardAmcId", jobcardAmcId);

    // Added on Vengatesh - mar-21-2026
    // if (!jobcardAmcId) {
    const warehouse = await this.workCenterlocationMatch();
    if (!warehouse) {
      this.hasSlotClicked = false;
      console.log("Warehouse not selected, stopping update.");
      return; // ✅ stops here
    }
    // }
    try {
      await this.updateJobCard();
      await this.loadJobCards();
    } catch (err) {
      console.error(err);
    } finally {
      this.hasSlotClicked = false;
    }
  }

  // Added on Vengatesh - mar-21-2026
  async workCenterlocationMatch() {
    // Mar 11 2026 Vengateshwaran S
    const stopFlow = (msg) => {
      this.hasSlotClicked = false;
      if (msg && this.notification) {
        this.notification.add(msg, { type: "info" });
      }
      return null;
    };

    this.hasSlotClicked = true;

    const taskId = this.state.selectedJobCardId;

    /* 1️⃣ Fetch task */
    const task = await this._getTask(taskId);
    if (!task) return;

    const categoryId = task.product_category_id?.[0];
    const categoryName = task.product_category_id?.[1];
    const workCenterId = task.work_center_id?.[0] || null;

    let warehouse = null;
    let lineIds = this.state.warehouseLineId;
    let technicianRequired = false;

    /* 2️⃣ CHECK WORK CENTER LOCATION CONDITION */
    if (workCenterId) {
      // const workCenterLocation = await this.orm.searchRead(
      //   "work.center.location",
      //   [
      //     ["id", "=", workCenterId],
      //     ["technician_warehouse_required_bool", "=", true],
      //   ],
      //   ["id"],
      // );
      const workCenterLocation = await this.orm.searchRead(
        "work.center.location",
        [["id", "=", workCenterId]],
        ["technician_warehouse_required_bool"],
      );

      // if (!workCenterLocation.length) {
      //   return stopFlow(
      //     "Technician warehouse is not required for this Work Center.",
      //   );
      // }
      if (workCenterLocation.length) {
        technicianRequired =
          workCenterLocation[0].technician_warehouse_required_bool;
      }
    }
    if (technicianRequired === true) {
      if (lineIds.length) {
        /* 3️⃣ Try from res.users.line */
        const lines = await this.orm.searchRead(
          "res.users.line",
          [
            ["id", "in", lineIds],
            ["product_category_line_id", "=", categoryId],
          ],
          ["warehouse_line_id"],
        );

        if (lines.length && lines[0].warehouse_line_id) {
          warehouse = lines[0].warehouse_line_id[0];
        }
        console.log("lineIds", warehouse);
      }
      console.log("lineIds", lineIds);

      /* 4️⃣ FALLBACK: work center + default + category */
      // if (!warehouse) {
      //   console.loh("warehouse-------------------------", warehouse);
      if (!workCenterId)
        return stopFlow("Work Center is not configured for this Job Card.");
      // let warehousedata = await this._findWarehouse([
      //   // ["work_center_id", "=", workCenterId],
      //   // ["region_default_warehouse_bool", "=", true],//-- no need
      //   ["product_category_ids", "in", [categoryId]],
      //   ["warehouse_type", "=", "technician_warehouse"],
      // ]);
      let warehousedata = await this.orm.searchRead(
        "stock.warehouse",
        [
          ["id", "=", warehouse],
          ["product_category_ids", "in", [categoryId]],
          ["warehouse_type", "=", "technician_warehouse"],
        ],
        ["id", "name", "warehouse_type"],
      );
      console.log("warehousedata ----------------------------", warehousedata);

      // warehouse = warehousedata?.id;
      warehouse = warehousedata?.[0]?.id;
      console.log("warehouse", warehouse);
    } else {
      if (!warehouse) {
        if (!workCenterId) {
          return stopFlow("Work Center is not configured for this Job Card.");
        }

        // let warehousedata = await this._findWarehouse([
        //   ["work_center_id", "=", workCenterId],
        //   //default warehouse - need
        //   ["region_default_warehouse_bool", "=", true],
        //   ["product_category_ids", "in", [categoryId]],
        //   ["warehouse_type", "=", "main_warehouse"], // changed here
        // ]);

        let warehousedata = await this.orm.searchRead(
          "stock.warehouse",
          [
            ["work_center_ids", "=", workCenterId],
            //default warehouse - need
            ["region_default_warehouse_bool", "=", true],
            ["product_category_ids", "in", [categoryId]],
            ["warehouse_type", "=", "main_warehouse"], // changed here
          ],
          ["id", "name", "warehouse_type"],
        );

        // warehouse = warehousedata?.id;
        console.log(
          "warehousedata technician required false ----------------------------",
          warehousedata,
        );
        warehouse = warehousedata?.[0]?.id;
        console.log(
          "warehouse  technician required false ----------------------",
          warehouse,
        );
      }
    }

    if (!warehouse) {
      let message = "";

      if (technicianRequired) {
        message = markup(
          _t(
            "Technician warehouse is not available for the technician <b>%s</b> to the Product category <b>%s</b>.",
            this.state.technicianName,
            categoryName,
          ),
        );
      } else {
        message = markup(
          _t(
            "Main warehouse is not available for the technician <b>%s</b> to the Product category <b>%s</b>.",
            this.state.technicianName,
            categoryName,
          ),
        );
      }

      this.dialog.add(ConfirmationDialog, {
        title: _t("Validation Error"),
        body: message,
      });
      // this.dialog.add(ConfirmationDialog, {
      //   title: _t("ValidationError"),
      //   // body: _t("No matching warehouse found for this Job Card.{taskId}"),
      //   body: _t(
      //     // "No matching warehouse found for this Job Card: %s",
      //     // this.state.jobCardNumber,
      //     "Technician warehouse is not available to the technician: %s",
      //     categoryName,
      //     this.state.technicianName,

      //     "Main warehouse is not available to the technician : %s",
      //     categoryName,
      //     this.state.technicianName,
      //   ),
      // });
      return;
      // return stopFlow("No matching warehouse found for this Job Card.");
    }

    /* ✅ SUCCESS */
    this.matchedWarehouseId = warehouse;
    console.log("Final resUserlineMatchJCPC Warehouse:", warehouse);

    this.hasSlotClicked = false;
    return warehouse;
  }

  // Added on Vengatesh - mar-21-2026
  //Feb 27-2025 VENGATESHWARAN S
  async _getTask(taskId) {
    const [task] = await this.orm.searchRead(
      "project.task",
      [["id", "=", taskId]],
      ["work_center_id", "product_category_id"],
    );

    // if (!task?.product_category_id) {
    //   this._error(_t("Product Category is not configured for the Job Card."));
    //   return null;
    // }

    return task;
  }

  // Added on Vengatesh - mar-21-2026
  async _findWarehouse(domain) {
    const res = await this.orm.searchRead("stock.warehouse", domain, [
      "id",
      "name",
      "warehouse_type", //workCenterlocationMatch
      "product_category_ids",
      "work_center_id",
    ]);
    console.log("warehousedata", res);
    return res.length ? res[0] : null;
  }
  _error(message) {
    this.notification.add(message, { type: "danger" });
    this.hasSlotClicked = false;
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
      console.log("taskData", taskData);

      if (taskData.length) {
        // Added on Vengatesh - mar-21-2026
        // get the first task record
        const task = taskData[0];

        // check if task has a warranty linked
        if (task.service_warranty_id?.length) {
          const warrantyId = task.service_warranty_id[0];

          const warrantyData = await this.orm.read(
            "service.warranty",
            [warrantyId],
            ["warranty_applicable_bool"],
          );
          console.log("warrantyData", warrantyData);

          // add warranty_applicable_bool to task object
          task.warranty_applicable_bool =
            warrantyData.length &&
            warrantyData[0].warranty_applicable_bool === false
              ? false
              : true; // or leave undefined if you only want to set false
        } else {
          // no warranty linked, optional default
          task.warranty_applicable_bool = false; // or false depending on your logic
        }
      }

      if (!taskData.length) {
        console.warn("No job card found with ID:", this.state.jobcardId);
        return;
      }

      // const task = taskData[0];
      // const isSecondVisit = task.second_visit_technician_bool;
      // const stateCode = parseInt(task.job_card_state_code, 10);
      // console.log("Second visit bool:", isSecondVisit);
      // console.log("Current state code:", stateCode);

      // Added on Vengatesh - mar-21-2026
      const task = taskData[0];
      let stateCode = parseInt(task.job_card_state_code, 10);
      const isUnitPullOutStatusCheck = task.unit_pull_out_status_check;
      const balanceAmountreceivedBool = task.balance_amount_received_bool;
      const warrantyApplicablebool = task.warranty_applicable_bool;
      const isSecondVisit = task.second_visit_technician_bool;
      console.log("unitPullOutStatusCheck", isUnitPullOutStatusCheck);
      console.log("balanceAmountreceivedBool", balanceAmountreceivedBool);
      console.log("warrantyApplicablebool", warrantyApplicablebool);
      console.log("state code-----------------------------", stateCode);
      console.log("Second visit bool:", isSecondVisit);
      let lastRescheduledStatusCode = "";
      let effectiveStateCode = "";

      if (
        // Added on Vengatesh - mar-21-2026
        warrantyApplicablebool === false &&
        stateCode === 127 &&
        isUnitPullOutStatusCheck === true &&
        balanceAmountreceivedBool === true
      ) {
        // Force workflow to "204" (example)
        const forcedStage = await this.orm.searchRead(
          "project.task.type",
          [["code", "=", "204"]],
          ["id", "code", "name"],
        );

        if (forcedStage.length) {
          this.state.job_card_state_code = parseInt(forcedStage[0].code);
          this.state.job_state = forcedStage[0].id;
          this.state.job_card_state = forcedStage[0].name;
        }
      } else if (stateCode === 107 && task.last_rescheduled_status_code) {
        effectiveStateCode = task.last_rescheduled_status_code;

        const stageLastResult = await this.orm.searchRead(
          "project.task.type",
          [["code", "=", effectiveStateCode]],
          ["id", "code", "name", "dynamic_job_state_code"],
        );

        console.log("stageLastResult", stageLastResult);

        if (stageLastResult.length) {
          this.state.job_card_state_code = parseInt(stageLastResult[0].code);
          this.state.job_state = stageLastResult[0].id;
          this.state.job_card_state = stageLastResult[0].name;

          // Optional: keep track of last rescheduled
          lastRescheduledStatusCode = effectiveStateCode;
          // }
        }
      } else {
        const stageResult = await this.orm.searchRead(
          "project.task.type",
          [["code", "=", stateCode]],
          ["id", "code", "name", "dynamic_job_state_code"],
        );
        const stageState = await this.orm.searchRead(
          "project.task.type",
          [["code", "=", stageResult[0].dynamic_job_state_code]],
          ["id", "code", "name", "scheduling_status_bool"],
        );

        this.state.job_card_state_code = parseInt(
          stageResult[0].dynamic_job_state_code,
        );
        this.state.job_state = stageState[0].id;
        this.state.job_card_state = stageState[0].name;
        lastRescheduledStatusCode = task.last_rescheduled_status_code || "";
        if (
          stageState.length &&
          stageState[0].scheduling_status_bool === true
        ) {
          lastRescheduledStatusCode = stageState[0].code || "";
        }
        console.log("lastRescheduledStatusCode", lastRescheduledStatusCode);
      }

      const values = {
        planned_date_begin: this.state.planned_date_begin,
        planned_date_end: this.state.planned_date_end,
        job_card_state_code: this.state.job_card_state_code,
        job_state: this.state.job_state,
        job_card_state: this.state.job_card_state,
        technician_id: this.state.teamId || null,
        warehouse_id: this.matchedWarehouseId || 181,
        // warehouse_id: this.state.warehouseId[0] || null,
        last_rescheduled_status_code: lastRescheduledStatusCode || "",
      };
      console.log("values", values);

      if (isSecondVisit && (stateCode === 132 || stateCode === 122)) {
        values.technician_second_visit_id = this.state.teamId;
      } else if (stateCode !== 117) {
        values.technician_first_visit_id = this.state.teamId;
      }

      if (Array.isArray(values.job_state)) {
        values.job_state = null; // keep only ID
      }

      Object.keys(values).forEach((key) => {
        if (values[key] === undefined) delete values[key];
      });

      console.log("✅ Final cleaned update values:", values);

      await this.orm.write("project.task", [this.state.jobcardId], values);

      await this.updateMachineRepairSupport(this.state.jobcardId, values);

      this.resetState();
    } catch (err) {
      console.error("❌ Failed to update job card:", err);
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

  // async updateMachineRepairSupport(jobcardId, payload) {
  //   const mrsRecords = await this.orm.searchRead(
  //     "machine.repair.support",
  //     [["task_id", "=", jobcardId]],
  //     ["id"]
  //   );

  //   if (!mrsRecords.length) return;

  //   const taskData = await this.orm.read(
  //     "project.task",
  //     [jobcardId],
  //     ["team_id", "technician_id", "planned_date_begin"]
  //   );

  //   const taskTeamId = taskData?.[0]?.team_id?.[0] || null;
  //   const plannedDateBegin = taskData?.[0]?.planned_date_begin || null;
  //   const technicianId = Array.isArray(taskData?.[0]?.technician_id)
  //     ? taskData[0].technician_id[0]
  //     : null;

  //   const valuesMRS = {
  //     task_id: jobcardId,
  //     service_request_state: payload.job_card_state || null,
  //     service_request_state_code: payload.job_card_state_code || null,
  //     user_id: technicianId || null,
  //     team_id: taskTeamId || null,
  //     call_request_appointment_date: this.state.serviceDatetime || null,
  //     technician_appointment_date: plannedDateBegin || null,
  //   };
  //   console.log("valuesMRS", valuesMRS);

  //   const mrsIds = mrsRecords.map((r) => r.id).filter((id) => !isNaN(id));

  //   if (mrsIds.length) {
  //     try {
  //       await this.orm.write("machine.repair.support", mrsIds, valuesMRS);
  //     } catch (err) {
  //       console.error("❌ Failed to update MRS:", err);
  //     }
  //   }

  //   setTimeout(() => {
  //     const nextArrows = document.querySelectorAll(".oi.oi-arrow-right");
  //     nextArrows.forEach((el) => el.click());
  //     const prevoiusarrows = document.querySelectorAll(".oi.oi-arrow-left");
  //     prevoiusarrows.forEach((el) => el.click());
  //   }, 2000);
  // }
  async updateMachineRepairSupport(jobcardId, values) {
    const mrsRecords = await this.orm.searchRead(
      "machine.repair.support",
      [["task_id", "=", jobcardId]],
      ["id"],
    );

    if (!mrsRecords.length) return;

    const taskData = await this.orm.read(
      "project.task",
      [jobcardId],
      [
        "team_id",
        "technician_id",
        "planned_date_begin",
        "job_card_state",
        "job_card_state_code",
      ],
    );
    console.log("taskdata", taskData);

    const taskTeamId = taskData?.[0]?.team_id?.[0] || null;
    const plannedDateBegin = taskData?.[0]?.planned_date_begin || null;
    const taskjobstate = values.job_card_state || null;
    const taskjobcardstatecode = taskData?.[0]?.job_card_state_code || null;
    const technicianId = Array.isArray(taskData?.[0]?.technician_id)
      ? taskData[0].technician_id[0]
      : null;

    const valuesMRS = {
      task_id: jobcardId,
      service_request_state: taskjobstate || null,
      service_request_state_code: taskjobcardstatecode || null,
      user_id: technicianId || null,
      team_id: taskTeamId || null,
      call_request_appointment_date: this.state.serviceDatetime || null,
      technician_appointment_date: plannedDateBegin || null,
    };
    console.log("valuesMRS", valuesMRS);

    const mrsIds = mrsRecords.map((r) => r.id).filter((id) => !isNaN(id));

    if (mrsIds.length) {
      try {
        await this.orm.write("machine.repair.support", mrsIds, valuesMRS);
      } catch (err) {
        console.error("❌ Failed to update MRS:", err);
      }
    }

    setTimeout(() => {
      const nextArrows = document.querySelectorAll(".oi.oi-arrow-right");
      nextArrows.forEach((el) => el.click());
      const prevoiusarrows = document.querySelectorAll(".oi.oi-arrow-left");
      prevoiusarrows.forEach((el) => el.click());
    }, 2000);
  }

  attachHighlightHandler() {
    const container = document.querySelector(
      ".o_gantt_view, .o_gantt, .o_content, .o_view_controller",
    );
    if (!container || container.dataset.highlightAttached) return;

    container.addEventListener("click", (ev) => this.handleSlotClick(ev));
    container.dataset.highlightAttached = "true";
  }

  handleSlotClick(ev) {
    const cell = ev.target.closest(
      "td[data-resource-id][data-date], td[data-date], .o_gantt_cell[data-date]",
    );
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

    const overlay = document.createElement("div");
    overlay.className = "jobcard-overlay";
    Object.assign(overlay.style, {
      position: "fixed",
      borderRadius: "6px",
      background: "rgba(255, 235, 59, 0.55)",
      outline: "2px solid rgba(255, 193, 7, 0.9)",
      pointerEvents: "none",
      zIndex: "9999",
      top: ev.clientY + "px",
      left: ev.clientX + "px",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "#000",
      fontWeight: "bold",
      fontSize: "11px",
      width: "100px",
      height: "25px",
    });
    overlay.textContent = `Technician: ${this.state.technicianName || "N/A"}`;
    document.body.appendChild(overlay);
    setTimeout(() => overlay.remove(), 100);
  }
}
registry.category("components").add("JobcardList", JobcardList);
