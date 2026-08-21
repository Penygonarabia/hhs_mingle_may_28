/** @odoo-module **/

import {
  useState,
  App,
  onMounted,
  onPatched,
  useEffect,
  onWillStart,
  useExternalListener,
} from "@odoo/owl";
import { useCalendarPopover, useClickHandler } from "@web/views/calendar/hooks";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { DomGanttCommonPopover } from "./domgantt_common_popover.esm";
import { DomGanttModelResource } from "./domgantt_model_resource.esm";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { templates } from "@web/core/assets";
import { useDebounced } from "@web/core/utils/timing";
import { useDomGantt } from "../hooks.esm";
import { useService } from "@web/core/utils/hooks";
import { MyComponent } from "../custom/component";
import { JobcardList } from "../custom/JobcardList";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { Dialog } from "@web/core/dialog/dialog";
import { session } from "@web/session";
// import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const MARKED_TITLE_SEPARATOR = "__DOMTTSEP__";
const SCALE_TO_FC_VIEW = {
  day: "resourceTimelineDay",
  week: "resourceTimelineWeek",
  month: "resourceTimelineMonth",
  year: "resourceTimelineYear",
};
// Centralized allowed job card states
const ALLOWED_JOB_CARD_STATES = [
  "101", // New
  "102", // Scheduled (Technician Assigned)
  "103", // Technician Accepted
  "104", // Technician Rejected
  "105", // Failed to attend call (Customer not answered)
  "106", // Out of City
  "107", // Rescheduled (Collect the re-schedule date & time @ the time of this request)
  "108", // Customer Accepted
  "109", // Technician Started
  "110", // Technician Reached
  "111", // Warranty Verification
  // "112", // Cancelled. Not Agree to Pay for Inspection (removed)
  "113", // Inspection Started
  "114", // Quotation provided. Waiting customer approval
  "115", // Job Started (In-progress)
  "116", // Payment Refused
  "117", // Unit Pull Out
  "118", // Unit Replaced
  "119", // Unit Returned
  "120", // Pending
  "121", // On Hold - Spare Parts Required
  "122", // Parts Ready
  "123", // Parts Received
  // "124", // Cancelled (removed)
  "125", // Ready to Invoice (Complete)
  // "126", // Closed (removed)
  "132", //"Unit Ready For Delivery"
  "133", //Rescheduled with Unit
  "134", //Rescheduled with Parts
  "152", //Requ. Visit
  "204", //Rescheduled  for Internal Technicinan
  "156",
  "207",
];

export class DomGanttCommonRenderer extends CalendarCommonRenderer {
  setup() {
    this.fc = useDomGantt("fullCalendar", this.gantt_options);
    this.click = useClickHandler(this.onClick, this.onDblClick);
    this.popover = useCalendarPopover(this.constructor.components.Popover);
    this.onWindowResizeDebounced = useDebounced(this.onWindowResize, 200);
    this.userIdToName = {};
    this.currentWorkCenterId = null;
    this.currentWorkCenterGroupId = null;
    this.usersNotInTasks = [];
    this.userColorMap = {};
    this.workCenterIdToName = {};
    this.userIdToWorkCenterId = {};
    this.resources = [];
    this.orm = useService("orm");
    this.user = useService("user");
    this.getjobcardStatecode(); // Preload once
    this.dialogService = useService("dialog");
    this.notification = useService("notification");
    this.holidays = [];
    this.state = useState({ loading: true });

    // =====================================================
    // ✅ PROJECT DROPDOWN STATE (NEW)
    // =====================================================
    this.projectState = useState({
      project_id: false,
      projects: [],
    });

    //    onWillStart(async () => {
    //        // Load project list
    //        this.projectState.projects = await this.orm.searchRead(
    //            "project.project",
    //            [],
    //            ["name"]
    //        );
    //
    //        // User Group Preload (existing logic)
    //        this.JobCardMobileUser = await this.user.hasGroup(
    //            "machine_repair_management.group_job_card_mobile_user"
    //        );
    //    });

    onWillStart(async () => {
      // Load project list
      const user = (
        await this.orm.searchRead(
          "res.users",
          [["id", "=", this.user.userId]],
          ["project_ids"],
        )
      )[0];

      // Fetch project records
      const projects = await this.orm.searchRead(
        "project.project",
        [["id", "in", user.project_ids]],
        ["id", "name"],
      );
      // this.projectState.project_id = user.project_ids[0];
      // this.projectState.projects = user.project_ids;

      this.projectState.projects = projects;
      // Auto select first project
      if (projects.length) {
        // <!-- may 20 2026 -->
        this.projectState.project_id = projects[0].id;
      }

      // Show dropdown only if more than one project
      this.projectState.showProjectSelector = projects.length > 1;// <!-- may 20 2026 -->
      console.log("this.projectState.project_id", this.projectState.project_id);
      console.log(" this.projectState.projects", this.projectState.projects);

      //        this.env.bus.trigger("project-filter-updated", {
      //            project_id: this.projectState.project_id,
      //        });
      //        console.log("")

      // User Group Preload (existing logic)
      this.JobCardMobileUser = await this.user.hasGroup(
        "machine_repair_management.group_job_card_mobile_user",
      );
    });

    const isRTL = session.user_context.lang.startsWith("ar");

    onMounted(async () => {
      //     // 🔥 Auto trigger the event here (works correctly)
      //    this.env.bus.trigger("project-filter-updated", {
      //        project_id: this.projectState.project_id,
      //    });
      // 🔥 Delay to ensure useBus listener is fully registered
      setTimeout(() => {
        console.log(
          "🔥 Auto Triggered (Delayed):",
          this.projectState.project_id,
        );
        this.env.bus.trigger("project-filter-updated", {
          project_id: this.projectState.project_id,
        });
      }, 300); // 300ms is enough

      console.log("Auto Triggered (onMounted):", this.projectState.project_id);
      const container = document.querySelector(
        // ".o_calendar_widget"
        ".o_calendar_widget",
      );
      if (container) {
        if (container) {
          container.style.direction = isRTL ? "rtl" : "ltr"; // ensures all children flow right-to-left
        }
      }
      // o_calendar_widget;
      // Show loader immediately
      this.state.loading = true;

      try {
        // Optional tiny delay to allow loader to render
        await new Promise((resolve) => browser.setTimeout(resolve, 2000));

        // Fetch all required data
        await this.fetchAllUsersAndTasks();
        this.resources = await this.mapRecordsToResources();
        this.listProjectTasks();
        this.scrollToTime();
        await this.loadHolidays();

        // Refresh calendar after data is ready
        if (this.fc.api) {
          this.fc.api.refetchResources();
          this.fc.api.refetchEvents();
        }
      } catch (err) {
        console.error("Error loading calendar data:", err);
        // Optional: show a notification
        this.notification.add({ title: "Calendar Load Error", type: "danger" });
      } finally {
        // Hide loader only after everything completes (success or error)
        this.state.loading = false;
      }
    });

    onPatched(() => {
      this.listProjectTasks();
      if (this.fc.api) {
        this.fc.api.refetchResources();
        this.fc.api.refetchEvents();
      }
    });

    useEffect(() => {
      this.updateSize();
      // this.fetchAllUsersAndTasks();
    });
    this.user = useService("user");

    onWillStart(async () => {
      this.JobCardMobileUser = await this.user.hasGroup(
        "machine_repair_management.group_job_card_mobile_user",
      );
      // console.log("📱 Is Job Card Mobile User:", this.JobCardMobileUser);
    });

    if (this.props.model.pagingEnable) {
      useExternalListener(window, "scroll", this.onWindowScroll, {
        passive: true,
      });
    }
  }

  //  onProjectChange(ev) {
  //    this.projectState.project_id = parseInt(ev.target.value) || false;
  //        if (this.fc?.api) {
  //            this.fc.api.refetchResources();
  //            this.fc.api.refetchEvents();
  //        }
  //    }

  onProjectChange(ev) {
    this.projectState.project_id = parseInt(ev.target.value) || false;
    console.log("this.projectState.project_id ", this.projectState.project_id);
    this.env.bus.trigger("project-filter-updated", {
      project_id: this.projectState.project_id,
    });

    // refetch USERS based on selected project
    this.fetchAllUsersAndTasks().then(() => {
      // then update FullCalendar
      if (this.fc?.api) {
        this.fc.api.refetchResources();
        this.fc.api.refetchEvents();
      }
    });
  }

  async loadHolidays() {
    try {
      const today = new Date();
      const year = today.getFullYear();
      const month = today.getMonth() + 1;

      let fyStart, fyEnd;
      if (month >= 4) {
        fyStart = `${year}-04-01 00:00:00`;
        fyEnd = `${year + 1}-03-31 23:59:59`;
      } else {
        fyStart = `${year - 1}-04-01 00:00:00`;
        fyEnd = `${year}-03-31 23:59:59`;
      }

      const leaves = await this.orm.searchRead(
        "resource.calendar.leaves",
        [
          ["date_from", "<=", fyEnd],
          ["date_to", ">=", fyStart],
        ],
        ["id", "name", "date_from", "date_to"],
      );

      console.log("Current FY Holidays:", leaves);
      this.holidays = leaves;
      this.highlightHolidaySlots();
      return leaves;
    } catch (err) {
      console.error("❌ Failed to load holidays:", err);
      this.holidays = [];
      return [];
    }
  }
  highlightHolidaySlots() {
    if (!this.holidays?.length) return;

    const applyHolidayStyles = () => {
      const slots = document.querySelectorAll("td[data-date]");

      slots.forEach((td) => {
        const slotDateStr = td.getAttribute("data-date");
        const slotDate = new Date(slotDateStr);

        // Check if this slot falls within any leave
        const holiday = this.holidays.find((h) => {
          const from = new Date(h.date_from.replace(" ", "T"));
          let to = new Date(h.date_to.replace(" ", "T"));

          // Handle 24:00:00 edge case
          if (h.date_to.endsWith("24:00:00")) {
            to.setHours(23, 59, 59, 999);
          }

          return slotDate >= from && slotDate <= to;
        });

        if (holiday) {
          td.classList.add("holiday");
          td.style.backgroundColor = "#28a745"; // green
          td.style.color = "#fff";

          // Insert description inside the inner div
          let innerDiv = td.querySelector("div");
          if (!innerDiv) {
            innerDiv = document.createElement("div");
            td.appendChild(innerDiv);
          }
          innerDiv.textContent = holiday.name || "Leave";
          innerDiv.style.fontSize = "10px";
          innerDiv.style.fontWeight = "bold";
          innerDiv.style.textAlign = "center";
          innerDiv.style.pointerEvents = "none";
        }
      });
    };

    // Run immediately
    applyHolidayStyles();

    // Observe dynamic changes in FullCalendar slots
    const fcContainer = document.querySelector(".fc-timeline-body");
    if (!fcContainer) return;

    const observer = new MutationObserver(() => applyHolidayStyles());
    observer.observe(fcContainer, { childList: true, subtree: true });
  }

  async getjobcardStatecode() {
    const taskTypeRecords = await this.env.services.orm.searchRead(
      "project.task.type",
      [["code", "!=", false]],
      ["code", "name"], // <-- Include name here
    );

    // Example: store array of objects with code + name
    this.jobCardStateCodes = taskTypeRecords.map((rec) => ({
      code: rec.code,
      name: rec.name,
    }));

    // console.log("✅ Full code-name list:", this.jobCardStateCodes);
    return this.jobCardStateCodes;
  }

  //  async fetchAllUsersAndTasks() {
  //    try {
  //      const userId = this.env.services.user?.userId || this.env.user?.uid;
  //
  //      const [currentUser] = await this.env.services.orm.read(
  //        "res.users",
  //        [userId],
  //        ["default_work_center_id", "name", "groups_id"]
  //      );
  //
  //      this.currentWorkCenterId = currentUser.default_work_center_id || [];
  //      const currentUserName = currentUser.name || "Unknown";
  //      const groupname = currentUser.groups_id;
  //
  //      // Get current user's work center group(s)
  //      let groupIds = [];
  //      if (this.currentWorkCenterId.length) {
  //        const workCenters = await this.env.services.orm.read(
  //          "work.center.location",
  //          this.currentWorkCenterId,
  //          ["work_center_group_id"]
  //        );
  //        groupIds = workCenters
  //          .map((wc) => wc.work_center_group_id?.[0])
  //          .filter(Boolean);
  //      }
  //
  //      this.currentWorkCenterGroupId = groupIds;
  //      const wcDomain = groupIds.length
  //        ? [["work_center_group_id", "in", groupIds]]
  //        : [];
  //
  //      const workCenters = await this.env.services.orm.searchRead(
  //        "work.center.location",
  //        wcDomain,
  //        ["id", "name"],
  //        { limit: 1000 }
  //      );
  //      const workCenterIds = workCenters.map((wc) => wc.id);
  //
  //      if (!workCenterIds.length) {
  //        this.env.services.notification.add(
  //          _t("No work centers found. Showing all users and tasks."),
  //          { type: "warning" }
  //        );
  //      }
  //
  //      //-------------------------------------------------------------------------------------------------
  //      const orm = this.env.services.orm;
  //
  //      // Step 1: Get the group ID for "Job Card Mobile User"
  //      const jobCardGroup = await orm.searchRead(
  //        "res.groups",
  //        [["name", "=", "Job Card Mobile User"]],
  //        ["id"]
  //      );
  //
  //      if (!jobCardGroup.length) {
  //        // console.warn("Group 'Job Card Mobile User' not found.");
  //        return;
  //      }
  //
  //      const jobCardGroupId = jobCardGroup[0].id;
  //
  //      // Step 2: Get all users matching your domain
  //      const userDomain = [
  //        ["active", "=", true],
  //        ["share", "=", false],
  //        ["id", "!=", userId],
  //      ];
  //
  //      if (workCenterIds.length) {
  //        userDomain.push(["default_work_center_id", "in", workCenterIds]);
  //      }
  //
  //      const users = await orm.searchRead("res.users", userDomain, [
  //        "id",
  //        "name",
  //        "login",
  //        "groups_id",
  //        "default_work_center_id",
  //      ]);
  //      console.log("users", users);
  //
  //      // Step 3: Filter users who are in 'Job Card Mobile User' group
  //      const filteredUsers = users.filter((u) =>
  //        u.groups_id.includes(jobCardGroupId)
  //      );
  //
  //      // console.log("Filtered Job Card Mobile Users:", filteredUsers);
  //      // -----------------------------------------------------------------------------------------------------------------------------
  //
  //      const colors = [
  //        "#FF6F61",
  //        "#6B5B95",
  //        "#88B04B",
  //        "#F7CAC9",
  //        "#92A8D1",
  //        "#955251",
  //        "#B565A7",
  //        "#009B77",
  //        "#DD4124",
  //        "#45B8AC",
  //
  //        "#0D47A1",
  //        "#1B5E20",
  //        "#E65100",
  //        "#4A148C",
  //        "#880E4F",
  //        "#006064",
  //        "#311B92",
  //        "#F57F17",
  //        "#004D40",
  //      ];
  //
  //      this.userIdToName = {};
  //      this.userColorMap = {};
  //      this.workCenterIdToName = {};
  //      this.userIdToWorkCenterId = {};
  //
  //      // Map WC name and user data
  //      const wcMap = {};
  //      const wcIdsToFetch = [
  //        ...new Set(
  //          users.map((u) => u.default_work_center_id?.[0]).filter(Boolean)
  //        ),
  //      ];
  //      console.log("wcIdsToFetch", wcIdsToFetch);
  //      if (wcIdsToFetch.length) {
  //        const wcDetails = await this.env.services.orm.read(
  //          "work.center.location",
  //          wcIdsToFetch,
  //          ["id", "name"]
  //        );
  //        wcDetails.forEach((wc) => {
  //          wcMap[wc.id] = wc.name;
  //          this.workCenterIdToName[wc.id] = wc.name;
  //        });
  //      }
  //
  //      users.forEach((user, index) => {
  //        const wcId = user.default_work_center_id?.[0] || null;
  //        this.userIdToName[user.id] = user.name;
  //        this.userColorMap[user.id] = colors[index % colors.length];
  //        this.userIdToWorkCenterId[user.id] =
  //          user.default_work_center_id || null;
  //        if (wcId && !this.workCenterIdToName[wcId]) {
  //          this.workCenterIdToName[wcId] = wcMap[wcId] || `Work Center ${wcId}`;
  //        }
  //      });
  //      // const wcMapKeys = new Set(Object.keys(wcMap));
  //
  //      // users.forEach((user, index) => {
  //      //   const [wcId, wcName] = user.default_work_center_id || [null, null];
  //
  //      //   // Map user data
  //      //   this.userIdToName[user.id] = user.name;
  //      //   this.userColorMap[user.id] = colors[index % colors.length];
  //      //   this.userIdToWorkCenterId[user.id] = wcId;
  //
  //      //   // Map work center name once
  //      //   if (wcId && !wcMapKeys.has(wcId)) {
  //      //     const name = wcName || `Work Center ${wcId}`;
  //      //     wcMap[wcId] = name;
  //      //     wcMapKeys.add(wcId);
  //      //   }
  //      //   this.workCenterIdToName[wcId] = wcMap[wcId];
  //      // });
  //
  //      // Fetch relevant tasks
  //      const taskDomain = [
  //        ...(workCenterIds.length
  //          ? [["work_center_id", "in", workCenterIds]]
  //          : []),
  //        // ["job_card_state_code", "in", ["101", "102", "107", "103"]],//30-08-2025
  //        ["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES],
  //      ];
  //
  //      const allTasks = await this.env.services.orm.searchRead(
  //        "project.task",
  //        taskDomain,
  //        [
  //          "id",
  //          "name",
  //          "work_center_id",
  //          "user_ids",
  //          "planned_date_begin",
  //          "planned_date_end",
  //          "job_card_state_code",
  //        ],
  //        { limit: 2000 }
  //      );
  //
  //      const assignedUserIds = new Set(
  //        allTasks.flatMap((task) => task.user_ids || [])
  //      );
  //      this.usersNotInTasks = Object.keys(this.userIdToName)
  //        .filter((id) => !assignedUserIds.has(+id))
  //        .map((id) => ({ id, name: this.userIdToName[id] }));
  //
  //      const records = Object.values(this.props.model.records || {});
  //      const filteredRecords = records.filter(
  //        (rec) =>
  //          (!workCenterIds.length ||
  //            workCenterIds.includes(rec.rawRecord.work_center_id?.[0]) ||
  //            !rec.rawRecord.work_center_id) &&
  //          ALLOWED_JOB_CARD_STATES.includes(rec.rawRecord.job_card_state_code)
  //      );
  //
  //      const userIdsFromRecords = new Set(
  //        filteredRecords.flatMap((rec) => rec.rawRecord.user_ids || [])
  //      );
  //    } catch (error) {
  //      this.env.services.notification.add(_t("Error fetching data."), {
  //        type: "danger",
  //      });
  //
  //      // Reset mappings
  //      this.userIdToName = {};
  //      this.userColorMap = {};
  //      this.workCenterIdToName = {};
  //      this.userIdToWorkCenterId = {};
  //    }
  //  }

  //  async fetchAllUsersAndTasks() {
  //    try {
  //        const userId = this.env.services.user?.userId || this.env.user?.uid;
  //
  //        const [currentUser] = await this.env.services.orm.read(
  //            "res.users",
  //            [userId],
  //            ["default_work_center_id", "name", "groups_id"]
  //        );
  //
  //        this.currentWorkCenterId = currentUser.default_work_center_id || [];
  //        const currentUserName = currentUser.name || "Unknown";
  //
  //        let groupIds = [];
  //        if (this.currentWorkCenterId.length) {
  //            const workCenters = await this.env.services.orm.read(
  //                "work.center.location",
  //                this.currentWorkCenterId,
  //                ["work_center_group_id"]
  //            );
  //
  //            groupIds = workCenters
  //                .map((wc) => wc.work_center_group_id?.[0])
  //                .filter(Boolean);
  //        }
  //
  //        this.currentWorkCenterGroupId = groupIds;
  //        const wcDomain = groupIds.length
  //            ? [["work_center_group_id", "in", groupIds]]
  //            : [];
  //
  //        const workCenters = await this.env.services.orm.searchRead(
  //            "work.center.location",
  //            wcDomain,
  //            ["id", "name"],
  //            { limit: 1000 }
  //        );
  //        const workCenterIds = workCenters.map((wc) => wc.id);
  //
  //        if (!workCenterIds.length) {
  //            this.env.services.notification.add(
  //                _t("No work centers found. Showing all users and tasks."),
  //                { type: "warning" }
  //            );
  //        }
  //
  //        //---------------------------------------------------------------------
  //        // USER GROUP
  //        //---------------------------------------------------------------------
  //        const orm = this.env.services.orm;
  //
  //        const jobCardGroup = await orm.searchRead(
  //            "res.groups",
  //            [["name", "=", "Job Card Mobile User"]],
  //            ["id"]
  //        );
  //
  //        if (!jobCardGroup.length) {
  //            return;
  //        }
  //
  //        const jobCardGroupId = jobCardGroup[0].id;
  //
  //        //---------------------------------------------------------------------
  //        // FULL USER DOMAIN
  //        //---------------------------------------------------------------------
  //        const userDomain = [
  //            ["active", "=", true],
  //            ["share", "=", false],
  //            ["id", "!=", userId],
  //        ];
  //
  //        if (workCenterIds.length) {
  //            userDomain.push(["default_work_center_id", "in", workCenterIds]);
  //        }
  //
  //        //---------------------------------------------------------------------
  //        // FETCH USERS (added project_ids)
  //        //---------------------------------------------------------------------
  //        const users = await orm.searchRead("res.users", userDomain, [
  //            "id",
  //            "name",
  //            "login",
  //            "groups_id",
  //            "default_work_center_id",
  //            "project_ids",   // 🔥 required for project filter
  //        ]);
  //
  //        //---------------------------------------------------------------------
  //        // PROJECT FILTER (MAIN REQUIREMENT)
  //        //---------------------------------------------------------------------
  //        const selectedProject = this.projectState?.project_id;
  //
  //        let projectFilteredUsers = users;
  //
  //        if (selectedProject) {
  //            projectFilteredUsers = users.filter((u) =>
  //                (u.project_ids || []).includes(selectedProject)
  //            );
  //        }
  //
  //        //---------------------------------------------------------------------
  //        // GROUP FILTER AFTER PROJECT FILTER
  //        //---------------------------------------------------------------------
  //        const filteredUsers = projectFilteredUsers.filter((u) =>
  //            u.groups_id.includes(jobCardGroupId)
  //        );
  //
  //        console.log("Final Users after project filter:", filteredUsers);
  //
  //        //---------------------------------------------------------------------
  //        // COLOR + WORK CENTER MAPPING
  //        //---------------------------------------------------------------------
  //        const colors = [
  //            "#FF6F61", "#6B5B95", "#88B04B", "#F7CAC9", "#92A8D1",
  //            "#955251", "#B565A7", "#009B77", "#DD4124", "#45B8AC",
  //            "#0D47A1", "#1B5E20", "#E65100", "#4A148C", "#880E4F",
  //            "#006064", "#311B92", "#F57F17", "#004D40"
  //        ];
  //
  //        this.userIdToName = {};
  //        this.userColorMap = {};
  //        this.workCenterIdToName = {};
  //        this.userIdToWorkCenterId = {};
  //
  //        const wcMap = {};
  //        const wcIdsToFetch = [
  //            ...new Set(
  //                users.map((u) => u.default_work_center_id?.[0]).filter(Boolean)
  //            ),
  //        ];
  //
  //        if (wcIdsToFetch.length) {
  //            const wcDetails = await this.env.services.orm.read(
  //                "work.center.location",
  //                wcIdsToFetch,
  //                ["id", "name"]
  //            );
  //            wcDetails.forEach((wc) => {
  //                wcMap[wc.id] = wc.name;
  //                this.workCenterIdToName[wc.id] = wc.name;
  //            });
  //        }
  //
  //        filteredUsers.forEach((user, index) => {
  //            const wcId = user.default_work_center_id?.[0] || null;
  //
  //            this.userIdToName[user.id] = user.name;
  //            this.userColorMap[user.id] = colors[index % colors.length];
  //            this.userIdToWorkCenterId[user.id] =
  //                user.default_work_center_id || null;
  //
  //            if (wcId && !this.workCenterIdToName[wcId]) {
  //                this.workCenterIdToName[wcId] = wcMap[wcId] || `Work Center ${wcId}`;
  //            }
  //        });
  //
  //        //---------------------------------------------------------------------
  //        // FETCH TASKS (NO CHANGE)
  //        //---------------------------------------------------------------------
  //        const taskDomain = [
  //            ...(workCenterIds.length
  //                ? [["work_center_id", "in", workCenterIds]]
  //                : []),
  //            ["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES],
  //        ];
  //
  //        const allTasks = await this.env.services.orm.searchRead(
  //            "project.task",
  //            taskDomain,
  //            [
  //                "id",
  //                "name",
  //                "work_center_id",
  //                "user_ids",
  //                "planned_date_begin",
  //                "planned_date_end",
  //                "job_card_state_code",
  //            ],
  //            { limit: 2000 }
  //        );
  //
  //        //---------------------------------------------------------------------
  //        // USERS WITHOUT TASKS
  //        //---------------------------------------------------------------------
  //        const assignedUserIds = new Set(
  //            allTasks.flatMap((task) => task.user_ids || [])
  //        );
  //
  //        this.usersNotInTasks = filteredUsers
  //            .filter((u) => !assignedUserIds.has(u.id))
  //            .map((u) => ({ id: u.id, name: u.name }));
  //
  //    } catch (error) {
  //        this.env.services.notification.add(_t("Error fetching data."), {
  //            type: "danger",
  //        });
  //
  //        this.userIdToName = {};
  //        this.userColorMap = {};
  //        this.workCenterIdToName = {};
  //        this.userIdToWorkCenterId = {};
  //    }
  //}

  //  async fetchAllUsersAndTasks() {
  //    try {
  //        const userId = this.env.services.user?.userId || this.env.user?.uid;
  //
  //        const [currentUser] = await this.env.services.orm.read(
  //            "res.users",
  //            [userId],
  //            ["default_work_center_id", "name", "groups_id"]
  //        );
  //
  //        this.currentWorkCenterId = currentUser.default_work_center_id || [];
  //        const currentUserName = currentUser.name || "Unknown";
  //
  //        // ------------------- WORK CENTER GROUP -------------------
  //        let groupIds = [];
  //        if (this.currentWorkCenterId.length) {
  //            const workCenters = await this.env.services.orm.read(
  //                "work.center.location",
  //                this.currentWorkCenterId,
  //                ["work_center_group_id"]
  //            );
  //
  //            groupIds = workCenters
  //                .map((wc) => wc.work_center_group_id?.[0])
  //                .filter(Boolean);
  //        }
  //
  //        this.currentWorkCenterGroupId = groupIds;
  //
  //        const wcDomain = groupIds.length
  //            ? [["work_center_group_id", "in", groupIds]]
  //            : [];
  //
  //        const workCenters = await this.env.services.orm.searchRead(
  //            "work.center.location",
  //            wcDomain,
  //            ["id", "name"]
  //        );
  //
  //        const workCenterIds = workCenters.map((wc) => wc.id);
  //
  //        if (!workCenterIds.length) {
  //            this.env.services.notification.add(
  //                _t("No work centers found. Showing all users and tasks."),
  //                { type: "warning" }
  //            );
  //        }
  //
  //        // ------------------- GROUP: Job Card Mobile User -------------------
  //        const orm = this.env.services.orm;
  //
  //        const jobCardGroup = await orm.searchRead(
  //            "res.groups",
  //            [["name", "=", "Job Card Mobile User"]],
  //            ["id"]
  //        );
  //
  //        if (!jobCardGroup.length) {
  //            return;
  //        }
  //
  //        const jobCardGroupId = jobCardGroup[0].id;
  //
  //        // ------------------- USER DOMAIN -------------------
  //        const userDomain = [
  //            ["active", "=", true],
  //            ["share", "=", false],
  //            ["id", "!=", userId],
  //        ];
  //
  //        if (workCenterIds.length) {
  //            userDomain.push(["default_work_center_id", "in", workCenterIds]);
  //        }
  //
  //        // ------------------- FETCH USERS (with project_ids) -------------------
  //        const users = await orm.searchRead("res.users", userDomain, [
  //            "id",
  //            "name",
  //            "login",
  //            "groups_id",
  //            "default_work_center_id",
  //            "project_ids",   // REQUIRED
  //        ]);
  //
  //        // -----------------------------------------------------
  //        // 🔥 PROJECT FILTER (MAIN REQUIREMENT)
  //        // -----------------------------------------------------
  //        const selectedProject = this.projectState?.project_id;
  //
  //        let projectFilteredUsers = users;
  //
  //        if (selectedProject) {
  //            projectFilteredUsers = users.filter((u) =>
  //                (u.project_ids || []).includes(selectedProject)
  //            );
  //        }
  //
  //        console.log("Users after project filter:", projectFilteredUsers);
  //
  //        // -----------------------------------------------------
  //        // 🔥 GROUP FILTER (Job Card Mobile User)
  //        // -----------------------------------------------------
  //        const filteredUsers = projectFilteredUsers.filter((u) =>
  //            u.groups_id.includes(jobCardGroupId)
  //        );
  //
  //        console.log("Users after group filter:", filteredUsers);
  //
  //        // -----------------------------------------------------
  //        // COLOR + WORK CENTER MAPPING
  //        // -----------------------------------------------------
  //        const colors = [
  //            "#FF6F61", "#6B5B95", "#88B04B", "#F7CAC9", "#92A8D1",
  //            "#955251", "#B565A7", "#009B77", "#DD4124", "#45B8AC",
  //            "#0D47A1", "#1B5E20", "#E65100", "#4A148C", "#880E4F",
  //            "#006064", "#311B92", "#F57F17", "#004D40"
  //        ];
  //
  //        this.userIdToName = {};
  //        this.userColorMap = {};
  //        this.workCenterIdToName = {};
  //        this.userIdToWorkCenterId = {};
  //
  //        const wcMap = {};
  //        const wcIdsToFetch = [
  //            ...new Set(
  //                filteredUsers.map((u) => u.default_work_center_id?.[0]).filter(Boolean)
  //            ),
  //        ];
  //
  //        if (wcIdsToFetch.length) {
  //            const wcDetails = await this.env.services.orm.read(
  //                "work.center.location",
  //                wcIdsToFetch,
  //                ["id", "name"]
  //            );
  //            wcDetails.forEach((wc) => {
  //                wcMap[wc.id] = wc.name;
  //                this.workCenterIdToName[wc.id] = wc.name;
  //            });
  //        }
  //
  //        filteredUsers.forEach((user, index) => {
  //            const wcId = user.default_work_center_id?.[0] || null;
  //
  //            this.userIdToName[user.id] = user.name;
  //            this.userColorMap[user.id] = colors[index % colors.length];
  //            this.userIdToWorkCenterId[user.id] =
  //                user.default_work_center_id || null;
  //
  //            if (wcId && !this.workCenterIdToName[wcId]) {
  //                this.workCenterIdToName[wcId] = wcMap[wcId] || `Work Center ${wcId}`;
  //            }
  //        });
  //
  //        // ------------------- FETCH TASKS -------------------
  //        const taskDomain = [
  //            ...(workCenterIds.length
  //                ? [["work_center_id", "in", workCenterIds]]
  //                : []),
  //            ["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES],
  //        ];
  //
  //        const allTasks = await this.env.services.orm.searchRead(
  //            "project.task",
  //            taskDomain,
  //            [
  //                "id",
  //                "name",
  //                "work_center_id",
  //                "user_ids",
  //                "planned_date_begin",
  //                "planned_date_end",
  //                "job_card_state_code",
  //            ]
  //        );
  //
  //        // ------------------- USERS WITHOUT TASKS -------------------
  //        const assignedUserIds = new Set(
  //            allTasks.flatMap((task) => task.user_ids || [])
  //        );
  //
  //        this.usersNotInTasks = filteredUsers
  //            .filter((u) => !assignedUserIds.has(u.id))
  //            .map((u) => ({ id: u.id, name: u.name }));
  //
  //    } catch (error) {
  //        this.env.services.notification.add(_t("Error fetching data."), {
  //            type: "danger",
  //        });
  //
  //        this.userIdToName = {};
  //        this.userColorMap = {};
  //        this.workCenterIdToName = {};
  //        this.userIdToWorkCenterId = {};
  //    }
  //}

  //    async fetchAllUsersAndTasks() {
  //    try {
  //        const userId = this.env.services.user?.userId || this.env.user?.uid;
  //
  //        const [currentUser] = await this.env.services.orm.read(
  //            "res.users",
  //            [userId],
  //            ["default_work_center_id", "name", "groups_id"]
  //        );
  //
  //        this.currentWorkCenterId = currentUser.default_work_center_id || [];
  //        const currentUserName = currentUser.name || "Unknown";
  //
  //        // ------------------- WORK CENTER GROUP -------------------
  //        let groupIds = [];
  //        if (this.currentWorkCenterId.length) {
  //            const workCenters = await this.env.services.orm.read(
  //                "work.center.location",
  //                this.currentWorkCenterId,
  //                ["work_center_group_id"]
  //            );
  //
  //            groupIds = workCenters
  //                .map((wc) => wc.work_center_group_id?.[0])
  //                .filter(Boolean);
  //        }
  //
  //        this.currentWorkCenterGroupId = groupIds;
  //
  //        const wcDomain = groupIds.length
  //            ? [["work_center_group_id", "in", groupIds]]
  //            : [];
  //
  //        const workCenters = await this.env.services.orm.searchRead(
  //            "work.center.location",
  //            wcDomain,
  //            ["id", "name"]
  //        );
  //
  //        const workCenterIds = workCenters.map((wc) => wc.id);
  //
  //        if (!workCenterIds.length) {
  //            this.env.services.notification.add(
  //                _t("No work centers found. Showing all users and tasks."),
  //                { type: "warning" }
  //            );
  //        }
  //
  //        // ------------------- GROUP: Job Card Mobile User -------------------
  //        const orm = this.env.services.orm;
  //
  //        const jobCardGroup = await orm.searchRead(
  //            "res.groups",
  //            [["name", "=", "Job Card Mobile User"]],
  //            ["id"]
  //        );
  //
  //        if (!jobCardGroup.length) {
  //            return;
  //        }
  //
  //        const jobCardGroupId = jobCardGroup[0].id;
  //
  //        // ------------------- USER DOMAIN -------------------
  //        const userDomain = [
  //            ["active", "=", true],
  //            ["share", "=", false],
  //            ["id", "!=", userId],
  //        ];
  //
  //        if (workCenterIds.length) {
  //            userDomain.push(["default_work_center_id", "in", workCenterIds]);
  //        }
  //
  //        // ------------------- FETCH USERS -------------------
  //        const users = await orm.searchRead("res.users", userDomain, [
  //            "id",
  //            "name",
  //            "login",
  //            "groups_id",
  //            "default_work_center_id",
  //            "project_ids",
  //        ]);
  //
  //        // -----------------------------------------------------
  //        // 🔥 PROJECT FILTER + REMOVE NO WORK CENTER USERS
  //        // -----------------------------------------------------
  //        const selectedProject = this.projectState?.project_id;
  //
  //        let projectFilteredUsers = users;
  //
  ////        if (selectedProject) {
  ////            // keep only users assigned to selected project
  ////            projectFilteredUsers = users.filter((u) =>
  ////                (u.project_ids || []).includes(selectedProject)
  ////            );
  ////
  ////            // Remove "User ID XXX (No Work Center)" dynamically
  ////            projectFilteredUsers = projectFilteredUsers.filter(
  ////                (u) => u.default_work_center_id && u.default_work_center_id.length
  ////            );
  ////        }
  //        if (selectedProject) {
  //            // keep only users assigned to project
  //            projectFilteredUsers = users.filter((u) =>
  //                (u.project_ids || []).includes(selectedProject)
  //            );
  //
  //            // remove users who have NO work center → remove from resource list completely
  //            projectFilteredUsers = projectFilteredUsers.filter(u =>
  //                u.default_work_center_id &&
  //                u.default_work_center_id.length > 0
  //            );
  //        }
  //
  //        console.log("Users after project filter:", projectFilteredUsers);
  //
  //        // -----------------------------------------------------
  //        // 🔥 GROUP FILTER (Job Card Mobile User)
  //        // -----------------------------------------------------
  //        const filteredUsers = projectFilteredUsers.filter((u) =>
  //            (u.groups_id || []).includes(jobCardGroupId)
  //        );
  //
  //        console.log("Users after group filter:", filteredUsers);
  //
  //        // ------------------- SORT: keep Unassigned separately (resource generator),
  ////        // then project users next (only matters among user rows)
  ////        if (selectedProject) {
  ////            filteredUsers.sort((a, b) => {
  ////                const aHas = (a.project_ids || []).includes(selectedProject);
  ////                const bHas = (b.project_ids || []).includes(selectedProject);
  ////                if (aHas && !bHas) return -1;
  ////                if (!aHas && bHas) return 1;
  ////                return 0;
  ////            });
  ////        }
  //        // -----------------------------------------------------
  //        // COLOR + WORK CENTER MAPPING
  //        // -----------------------------------------------------
  //        const colors = [
  //            "#FF6F61", "#6B5B95", "#88B04B", "#F7CAC9", "#92A8D1",
  //            "#955251", "#B565A7", "#009B77", "#DD4124", "#45B8AC",
  //            "#0D47A1", "#1B5E20", "#E65100", "#4A148C", "#880E4F",
  //            "#006064", "#311B92", "#F57F17", "#004D40"
  //        ];
  //
  //        this.userIdToName = {};
  //        this.userColorMap = {};
  //        this.workCenterIdToName = {};
  //        this.userIdToWorkCenterId = {};
  //
  //        const wcMap = {};
  //        const wcIdsToFetch = [
  //            ...new Set(
  //                filteredUsers.map((u) => u.default_work_center_id?.[0]).filter(Boolean)
  //            ),
  //        ];
  //
  //        if (wcIdsToFetch.length) {
  //            const wcDetails = await this.env.services.orm.read(
  //                "work.center.location",
  //                wcIdsToFetch,
  //                ["id", "name"]
  //            );
  //            wcDetails.forEach((wc) => {
  //                wcMap[wc.id] = wc.name;
  //                this.workCenterIdToName[wc.id] = wc.name;
  //            });
  //        }
  //
  //        filteredUsers.forEach((user, index) => {
  //            const wcId = user.default_work_center_id?.[0] || null;
  //
  //            this.userIdToName[user.id] = user.name;
  //            this.userColorMap[user.id] = colors[index % colors.length];
  //            this.userIdToWorkCenterId[user.id] =
  //                user.default_work_center_id || null;
  //
  //            if (wcId && !this.workCenterIdToName[wcId]) {
  //                this.workCenterIdToName[wcId] = wcMap[wcId] || `Work Center ${wcId}`;
  //            }
  //        });
  //
  //        // ------------------- FETCH TASKS -------------------
  //        const taskDomain = [
  //            ...(workCenterIds.length
  //                ? [["work_center_id", "in", workCenterIds]]
  //                : []),
  //            ["job_card_state_code", "in", ALLOWED_JOB_CARD_STATES],
  //        ];
  //
  //        const allTasks = await this.env.services.orm.searchRead(
  //            "project.task",
  //            taskDomain,
  //            [
  //                "id",
  //                "name",
  //                "work_center_id",
  //                "user_ids",
  //                "planned_date_begin",
  //                "planned_date_end",
  //                "job_card_state_code",
  //            ]
  //        );
  //
  //        // ------------------- USERS WITHOUT TASKS -------------------
  //        const assignedUserIds = new Set(
  //            allTasks.flatMap((task) => task.user_ids || [])
  //        );
  //
  //        this.usersNotInTasks = filteredUsers
  //            .filter((u) => !assignedUserIds.has(u.id))
  //            .map((u) => ({ id: u.id, name: u.name }));
  //
  //    } catch (error) {
  //        this.env.services.notification.add(_t("Error fetching data."), {
  //            type: "danger",
  //        });
  //
  //        this.userIdToName = {};
  //        this.userColorMap = {};
  //        this.workCenterIdToName = {};
  //        this.userIdToWorkCenterId = {};
  //    }
  //}

  //Added on 2025-11-16
  async fetchAllUsersAndTasks() {
    try {
      const userId = this.env.services.user?.userId || this.env.user?.uid;

      const [currentUser] = await this.env.services.orm.read(
        "res.users",
        [userId],
        ["default_work_center_id", "name", "groups_id"],
      );

      this.currentWorkCenterId = currentUser.default_work_center_id || [];

      // ---------------- WORK CENTER GROUP ----------------
      let groupIds = [];
      if (this.currentWorkCenterId.length) {
        const workCenters = await this.env.services.orm.read(
          "work.center.location",
          this.currentWorkCenterId,
          ["work_center_group_id"],
        );

        groupIds = workCenters
          .map((wc) => wc.work_center_group_id?.[0])
          .filter(Boolean);
      }

      this.currentWorkCenterGroupId = groupIds;

      const wcDomain = groupIds.length
        ? [["work_center_group_id", "in", groupIds]]
        : [];

      const workCenters = await this.env.services.orm.searchRead(
        "work.center.location",
        wcDomain,
        ["id", "name"],
      );

      const workCenterIds = workCenters.map((wc) => wc.id);

      // ---------------- GROUP: Job Card Mobile User ----------------
      const orm = this.env.services.orm;

      const jobCardGroup = await orm.searchRead(
        "res.groups",
        [["name", "=", "Job Card Mobile User"]],
        ["id"],
      );

      if (!jobCardGroup.length) return;
      const jobCardGroupId = jobCardGroup[0].id;

      // ---------------- USER DOMAIN ----------------
      const userDomain = [
        ["active", "=", true],
        ["share", "=", false],
        ["id", "!=", userId],
      ];

      if (workCenterIds.length) {
        userDomain.push(["default_work_center_id", "in", workCenterIds]);
      }

      // ---------------- FETCH USERS ----------------
      const users = await orm.searchRead("res.users", userDomain, [
        "id",
        "name",
        "login",
        "groups_id",
        "default_work_center_id",
        "project_ids",
      ]);

      const selectedProject = this.projectState?.project_id;

      let projectFilteredUsers = users;

      if (selectedProject) {
        projectFilteredUsers = users.filter((u) =>
          (u.project_ids || []).includes(selectedProject),
        );

        // Remove users with NO WORK CENTER dynamically
        projectFilteredUsers = projectFilteredUsers.filter(
          (u) => u.default_work_center_id && u.default_work_center_id.length,
        );
      }

      const filteredUsers = projectFilteredUsers.filter((u) =>
        (u.groups_id || []).includes(jobCardGroupId),
      );

      // ---------------- STORE MAPPINGS ----------------
      this.userIdToName = {};
      this.userColorMap = {};
      this.workCenterIdToName = {};
      this.userIdToWorkCenterId = {};

      // const wcIdsToFetch = [
      //   ...new Set(
      //     filteredUsers
      //       .map((u) => u.default_work_center_id?.[0])
      //       .filter(Boolean),
      //   ),
      // ];
      // Code Added on August 18 2026 Work center displayed 
      const wcIdsToFetch = [
        ...new Set(
          filteredUsers.flatMap((u) => u.default_work_center_id || []),
        ),
      ];

      if (wcIdsToFetch.length) {
        const wcDetails = await orm.read("work.center.location", wcIdsToFetch, [
          "id",
          "name",
        ]);

        wcDetails.forEach((wc) => {
          this.workCenterIdToName[wc.id] = wc.name;
        });
      }

      filteredUsers.forEach((user) => {
        const wcId = user.default_work_center_id?.[0] || null;

        this.userIdToName[user.id] = user.name;
        this.userIdToWorkCenterId[user.id] = user.default_work_center_id;
      });

      // -------------- BUILD RESOURCES (REMOVE UNDEFINED) --------------

      this.resources = filteredUsers
        .filter((u) => u && u.id && u.name) // REMOVE undefined users
        .map((u) => ({
          id: String(u.id),
          title: u.name,
          extendedProps: {
            //                    employee_no: u.login || "",
            work_center_id: u.default_work_center_id?.[0] || null,
          },
        }));

      // ALWAYS ADD UNASSIGNED AT TOP
      this.resources.unshift({
        id: "unassigned",
        title: "Unassigned",
        extendedProps: {},
      });
    } catch (err) {
      this.env.services.notification.add(_t("Error fetching data."), {
        type: "danger",
      });

      this.resources = [];
    }
  }

  listProjectTasks() {
    const workCenterIds = Object.keys(this.workCenterIdToName).map((id) =>
      parseInt(id),
    );
    // console.log("workCenterIds", workCenterIds);
    const records = Object.values(this.props.model.records).filter(
      (record) =>
        (!workCenterIds.length ||
          workCenterIds.includes(record.rawRecord.work_center_id?.[0]) ||
          !record.rawRecord.work_center_id) &&
        ALLOWED_JOB_CARD_STATES.includes(record.rawRecord.job_card_state_code),
    );

    const unassignedTasks = records.filter(
      (record) =>
        !record.rawRecord.user_ids || record.rawRecord.user_ids.length === 0,
    );
  }

  scrollToTime() {
    browser.setTimeout(() => {
      if (this.fc.api?.view) {
        const toDay = luxon?.DateTime
          ? luxon.DateTime.now().setZone("Asia/Riyadh")
          : new Date();
        if (this.props.model.scale === "day") {
          this.fc.api.scrollToTime(
            luxon?.DateTime
              ? toDay.toFormat("HH:mm")
              : toDay.toLocaleTimeString(),
          );
        } else if (this.props.model.scale === "week") {
          const startOfWeek = luxon?.DateTime
            ? toDay.startOf("week")
            : new Date(toDay.setDate(toDay.getDate() - toDay.getDay()));

          this.fc.api.gotoDate(
            luxon?.DateTime
              ? startOfWeek.toISODate()
              : startOfWeek.toISOString().split("T")[0],
          );
        } else {
          this.fc.api.scrollToTime({
            month: luxon?.DateTime
              ? toDay.toObject().month - 1
              : toDay.getMonth(),
          });
        }
      }
    }, 0);
  }

  get gantt_options() {
    const options = this.cleanOptions(this.options || {});
    const options_extra = {
      initialView: SCALE_TO_FC_VIEW[this.props.model.scale],
      displayEventTime: !this.props.model.meta.isTimeHidden,
      displayEventEnd: !this.props.model.meta.isTimeEndHidden,
      weekends: true,
      weekNumbers: false,
      resourceAreaHeaderContent: "",
      resourceAreaColumns: this._getResourceAreaColumns(),
      resources: (_, successRS) => {
        successRS(this.resources);
      },
      resourceLabelDidMount: this.onResourceLabelDidMount,
      resourceLabelContent: this.onResourceLabelContent.bind(this),
      eventAdd: this.onEventAdd,
      eventChange: this.onEventChange,
      eventRemove: this.onEventRemove,
      eventsSet: this.onEventSet,
      editable: true,
      selectable: true,
      eventDrop: this.onEventDrop.bind(this),
      eventDragStart: this.onEventDragStart.bind(this),
      eventDragStop: this.onEventDragStop.bind(this),

      // oct-14-2025
      eventContent: () => ({ domNodes: [] }),
      // Custom event renderer (from previous code)
      eventDidMount: this.onEventRender.bind(this), // oct-14-2025

      events: async (info, successCallback) => {
        const events = await Promise.all(
          Object.values(this.props.model.records)
            .filter((record) =>
              ALLOWED_JOB_CARD_STATES.includes(
                record.rawRecord.job_card_state_code,
              ),
            )
            .map((record) => this.convertRecordToEvent(record)),
        );

        const filteredEvents = events.filter((event) => event !== null);
        successCallback(filteredEvents);
      },
    };

    options_extra.resourceOrder = (a, b) => {
      if (a.id === "unassigned") return -1;
      if (b.id === "unassigned") return 1;
      const resourceOrders = this._getResourceOrders();
      if (resourceOrders && resourceOrders.key) {
        return a[resourceOrders.key] < b[resourceOrders.key] ? -1 : 1;
      }
      return 0;
    };

    if (this.props.model.meta.resourceWidth) {
      options_extra.resourceAreaWidth = this.props.model.meta.resourceWidth;
    } else {
      options_extra.resourceAreaWidth = "200px";
    }
    if (this.props.model.meta.slotMinWidth) {
      options_extra.slotMinWidth = this.props.model.meta.slotMinWidth;
    }
    if (this.props.model.meta.resourceGroupField) {
      options_extra.resourceGroupField =
        this.props.model.meta.resourceGroupField;
    }
    if (this.props.model.meta.eventTimeFormatDigits) {
      options_extra.eventTimeFormat = {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      };
    }
    //        let nowDate = luxon?.DateTime ? luxon.DateTime.local().setZone("Asia/Kolkata") : new Date();
    let nowDate = luxon?.DateTime
      ? luxon.DateTime.local().setZone("Asia/Riyadh")
      : new Date();

    if (
      nowDate < this.props.model.data.range.start ||
      nowDate > this.props.model.data.range.end
    ) {
      nowDate = this.props.model.data.range.start;
      options_extra.nowIndicator = false;
    }
    options_extra.now = luxon?.DateTime
      ? nowDate.toString()
      : nowDate.toISOString();
    Object.assign(options, options_extra);
    return options;
  }
  // oct-11-2025
  // async onEventDrop(info) {
  //   const { event, revert } = info;
  //   const newResource = event.getResources()[0];
  //   const recordId = event.id;
  //   const record = this.props.model.records[recordId];

  //   if (!newResource || !record) {
  //     revert();
  //     this.env.services.notification.add(
  //       _t("Cannot move event: Invalid resource or record"),
  //       { type: "danger" }
  //     );
  //     return;
  //   }

  //   const oldResources = event.getResources();
  //   const oldStart = event.start;
  //   const oldEnd = event.end;

  //   const newUserId =
  //     newResource.id === "unassigned" ? null : parseInt(newResource.id);

  //   if (newResource.id !== "unassigned" && isNaN(newUserId)) {
  //     revert();
  //     this.env.services.notification.add(
  //       _t("Cannot move event: Invalid user ID"),
  //       { type: "danger" }
  //     );
  //     return;
  //   }

  //   const currentTime = luxon.DateTime.now();
  //   const newStartTime = event.start
  //     ? luxon.DateTime.fromJSDate(event.start)
  //     : null;

  //   if (!newStartTime) {
  //     revert();
  //     this.env.services.notification.add(
  //       _t("Cannot move event: Invalid start date"),
  //       { type: "danger" }
  //     );
  //     return;
  //   }

  //   // Disallow Friday (5) and Saturday (6)
  //   const startWeekday = newStartTime.weekday;
  //   if (startWeekday === 5 || startWeekday === 6) {
  //     this.env.services.notification.add(
  //       _t("Cannot schedule on Friday or Saturday."),
  //       { type: "danger" }
  //     );
  //     revert();
  //     return;
  //   }

  //   // Validate date based on scale
  //   const scale = this.props.model.scale;
  //   let isValidDate = false;
  //   if (scale === "day") {
  //     isValidDate = newStartTime > currentTime;
  //   } else if (["week", "month", "year"].includes(scale)) {
  //     isValidDate = newStartTime.startOf("day") >= currentTime.startOf("day");
  //   } else {
  //     isValidDate = newStartTime > currentTime;
  //   }
  //   if (!isValidDate) {
  //     revert();
  //     this.env.services.notification.add(
  //       _t("Cannot move event: The start date must be in the future."),
  //       { type: "danger" }
  //     );
  //     return;
  //   }

  //   const formatOdooDate = (date) => {
  //     if (!date) return null;
  //     return luxon.DateTime.fromJSDate(date)
  //       .minus({ hours: 3 })
  //       .toFormat("yyyy-MM-dd HH:mm:ss");
  //   };

  //   const stateCode = record.rawRecord.job_card_state_code;
  //   const userId = record.rawRecord.user_ids?.[0];

  //   const userName = this.userIdToName[userId] || "Unassigned";

  //   console.log("userState", userName);
  //   function toAsciiDigits(str) {
  //     const arabicDigits = "٠١٢٣٤٥٦٧٨٩";
  //     return str.replace(/[٠-٩]/g, (d) => arabicDigits.indexOf(d));
  //   }
  //   console.log("record-------------->", record);

  //   if (stateCode === "101" || stateCode === "102") {
  //     const updateData = {
  //       user_ids: newUserId ? [[6, 0, [newUserId]]] : [[5]],
  //     };
  //     // if (newResource.id === "unassigned") {
  //     //   updateData.planned_date_begin = false;
  //     //   updateData.planned_date_end = false;
  //     //   updateData.job_card_state_code = 101;
  //     //   updateData.job_state = "";
  //     //   updateData.job_card_state = "New";
  //     //   updateData.technician_first_visit_id = null;
  //     //   updateData.technician_second_visit_id = null;
  //     // } else {
  //     //   updateData.planned_date_begin = event.start
  //     //     ? toAsciiDigits(formatOdooDate(event.start))
  //     //     : toAsciiDigits(record.rawRecord.planned_date_begin);

  //     //   updateData.planned_date_end = event.end
  //     //     ? toAsciiDigits(formatOdooDate(event.end))
  //     //     : toAsciiDigits(record.rawRecord.planned_date_end);
  //     //   let technicianId = newResource.id;
  //     //   console.log("Technician ID:", technicianId);

  //     //   const result = await this.env.services.orm.read(
  //     //     "project.task", // model
  //     //     [parseInt(recordId)], // single record ID
  //     //     ["second_visit_technician_bool"] // fields to fetch
  //     //   );

  //     //   const secondVisitBool =
  //     //     result?.[0]?.second_visit_technician_bool ?? null;
  //     //   console.log("Second Visit Bool:", secondVisitBool);

  //     //   // Assign technician depending on secondVisitBool
  //     //   if (secondVisitBool) {
  //     //     // Second visit is true → assign to second_visit_technician_id
  //     //     updateData.technician_second_visit_id = technicianId
  //     //       ? parseInt(technicianId, 10)
  //     //       : false;
  //     //   } else {
  //     //     // First visit → assign to first_visit
  //     //     updateData.technician_first_visit_id = technicianId
  //     //       ? parseInt(technicianId, 10)
  //     //       : false;
  //     //   }

  //     //   console.log("Final updateData:", updateData);
  //     // }

  //     if (newResource.id === "unassigned") {
  //       // 🔸 Reset task when unassigned
  //       Object.assign(updateData, {
  //         planned_date_begin: false,
  //         planned_date_end: false,
  //         job_card_state_code: 101,
  //         job_card_state: "New",
  //         job_state: "",
  //         technician_first_visit_id: false,
  //         technician_second_visit_id: false,
  //       });

  //       console.log("🟠 Unassigned task — cleared technician and schedule.");

  //       // 🔹 Try updating linked machine.repair.support
  //       const machineRecords = await this.env.services.orm.searchRead(
  //         "machine.repair.support",
  //         [["task_id.id", "=", parseInt(recordId, 10)]],
  //         ["id"]
  //       );

  //       if (machineRecords.length === 0) {
  //         console.log(
  //           "⚠️ No machine.repair.support records found for this task."
  //         );
  //       } else {
  //         const machineIds = machineRecords.map((rec) => rec.id);
  //         console.log("🔹 Updating linked machine.repair.support:", machineIds);

  //         await this.env.services.orm.write(
  //           "machine.repair.support",
  //           machineIds,
  //           {
  //             service_request_state: "New",
  //             service_request_state_code: 101,
  //             user_id: null,
  //             technician_appointment_date: null,
  //           }
  //         );
  //       }
  //     } else {
  //       // 🔹 Handle assigned technician case
  //       const technicianId = parseInt(newResource.id, 10);

  //       Object.assign(updateData, {
  //         planned_date_begin: event.start
  //           ? toAsciiDigits(formatOdooDate(event.start))
  //           : toAsciiDigits(record.rawRecord.planned_date_begin),
  //         planned_date_end: event.end
  //           ? toAsciiDigits(formatOdooDate(event.end))
  //           : toAsciiDigits(record.rawRecord.planned_date_end),
  //       });

  //       const [taskData] = await this.env.services.orm.read(
  //         "project.task",
  //         [parseInt(recordId, 10)],
  //         ["second_visit_technician_bool"]
  //       );

  //       const secondVisitBool = !!taskData?.second_visit_technician_bool;
  //       console.log("📋 second_visit_technician_bool:", secondVisitBool);

  //       if (secondVisitBool) {
  //         updateData.technician_second_visit_id = technicianId;
  //         updateData.technician_first_visit_id = false;
  //       } else {
  //         updateData.technician_first_visit_id = technicianId;
  //         updateData.technician_second_visit_id = false;
  //       }

  //       // 🔹 Update machine.repair.support if found
  //       const machineRecords = await this.env.services.orm.searchRead(
  //         "machine.repair.support",
  //         [["task_id.id", "=", parseInt(recordId, 10)]],
  //         ["id"]
  //       );

  //       if (machineRecords.length === 0) {
  //         console.log(
  //           "⚠️ No machine.repair.support records found for this task."
  //         );
  //       } else {
  //         const machineIds = machineRecords.map((rec) => rec.id);
  //         console.log("🔹 Updating linked machine.repair.support:", machineIds);

  //         let teamId = null;

  //         const machineTeam = await this.env.services.orm.searchRead(
  //           "machine.support.team",
  //           [["leader_id.id", "=", technicianId]],
  //           ["id", "leader_id"]
  //         );

  //         console.log("machineTeam:", machineTeam);

  //         if (machineTeam.length > 0) {
  //           teamId = machineTeam[0].id;
  //           console.log("✅ Team ID found:", teamId);
  //         } else {
  //           console.log(
  //             "⚠️ No matching team found for leader_id =",
  //             technicianId
  //           );
  //         }

  //         await this.env.services.orm.write(
  //           "machine.repair.support",
  //           machineIds,
  //           {
  //             service_request_state: updateData.job_card_state || null,
  //             service_request_state_code:
  //               updateData.job_card_state_code || null,
  //             user_id: technicianId ? parseInt(technicianId, 10) : null,
  //             team_id: teamId ? parseInt(teamId, 10) : false,
  //             technician_appointment_date:
  //               updateData.planned_date_begin || null,
  //           }
  //         );

  //         console.log("✅ machine.repair.support updated successfully!");
  //       }

  //       console.log("✅ Final updateData:", updateData);
  //     }

  //     console.log("updata", updateData);

  //     // Confirmation dialog
  //     const confirmed = await this.env.services.dialog.add(ConfirmationDialog, {
  //       title: _t("Confirm Task Update"),
  //       body:
  //         newResource.id === "unassigned"
  //           ? _t("Are you sure you want to unassign this task?")
  //           : _t(
  //               `Are you sure you want to assign this task to ${
  //                 newResource.title || "the user"
  //               }?`
  //             ),
  //       confirm: async () => {
  //         try {
  //           console.log("📤 Updating project.task:", {
  //             recordId: parseInt(recordId),
  //             updateData,
  //           });
  //           await this.env.services.orm.write(
  //             "project.task",
  //             [parseInt(recordId)],
  //             updateData
  //           );

  //           if (newResource.id === "unassigned") {
  //             const machineRecords = await this.env.services.orm.searchRead(
  //               "machine.repair.support",
  //               [["task_id.id", "=", parseInt(recordId, 10)]],
  //               ["id"]
  //             );

  //             if (machineRecords.length > 0) {
  //               // Collect IDs in an array
  //               const machineIds = machineRecords.map((rec) => rec.id);

  //               // 🔹 Log the data before update
  //               console.log("Updating machine.repair.support records:", {
  //                 machineIds,
  //                 service_request_state: updateData.job_card_state || null,
  //                 service_request_state_code:
  //                   updateData.job_card_state_code || null,
  //                 user_id:
  //                   newResource.id === "unassigned"
  //                     ? null
  //                     : parseInt(newResource.id),
  //                 team_id: null,
  //                 technician_appointment_date:
  //                   updateData.planned_date_begin || null,
  //               });

  //               // Update the records
  //               await this.env.services.orm.write(
  //                 "machine.repair.support",
  //                 machineIds, // ✅ must be array of IDs
  //                 {
  //                   service_request_state: updateData.job_card_state || null,
  //                   service_request_state_code:
  //                     updateData.job_card_state_code || null,
  //                   user_id:
  //                     newResource.id === "unassigned"
  //                       ? null
  //                       : parseInt(newResource.id),
  //                   team_id: null,
  //                   technician_appointment_date:
  //                     updateData.planned_date_begin || null,
  //                 }
  //               );
  //             }
  //           }

  //           event.setResources(newUserId ? [newUserId] : []);
  //           let message, type;
  //           if (newUserId && newUserId !== "unassigned") {
  //             message = _t("Technician has been assigned successfully");
  //             type = "success";
  //           } else {
  //             message = _t("♻️ Job card list refreshed after unassignment");
  //             type = "info";
  //           }

  //           // Show notification
  //           this.env.services.notification.add(message, { type });

  //           // Optional: timeline label
  //           const labelEl = document.createElement("div");
  //           labelEl.classList.add("gantt-label");
  //           labelEl.textContent = `Moved: Start ${
  //             event.start
  //               ? luxon.DateTime.fromJSDate(event.start).toFormat(
  //                   "M/d/yyyy, h:mm a"
  //                 )
  //               : "N/A"
  //           }`;
  //           labelEl.style.position = "absolute";
  //           labelEl.style.backgroundColor = "#ffffff";
  //           labelEl.style.padding = "2px 5px";
  //           labelEl.style.borderRadius = "3px";
  //           labelEl.style.zIndex = "1000";

  //           const timelineContainer = document.querySelector(".fc-timeline");
  //           if (timelineContainer) {
  //             const eventLeft = info.el.offsetLeft;
  //             labelEl.style.left = `${eventLeft}px`;
  //             labelEl.style.top = "0px";
  //             timelineContainer.appendChild(labelEl);
  //             setTimeout(() => labelEl.remove(), 5000);
  //           }

  //           await this.fetchAllUsersAndTasks();
  //           this.resources = await this.mapRecordsToResources();
  //           this.listProjectTasks();
  //           if (newResource.id === "unassigned") {
  //             // ✅ Notify JobcardList to refresh
  //             this.env.bus.trigger("jobcard-unassigned");
  //           } else {
  //             // Assigned task logic
  //             setTimeout(() => {
  //               const nextArrows =
  //                 document.querySelectorAll(".oi.oi-arrow-right");
  //               nextArrows.forEach((el) => el.click());
  //               const previousArrows =
  //                 document.querySelectorAll(".oi.oi-arrow-left");
  //               previousArrows.forEach((el) => el.click());
  //             }, 2000);
  //           }

  //           return true;
  //         } catch (error) {
  //           this.env.services.notification.add(
  //             _t(`Failed to move event: ${error.message || "Unknown error"}`),
  //             { type: "danger" }
  //           );
  //           return false;
  //         }
  //       },
  //       cancel: async () => {
  //         // Revert to old data
  //         event.setResources(oldResources);
  //         if (oldStart) event.setStart(oldStart);
  //         if (oldEnd) event.setEnd(oldEnd);
  //         setTimeout(() => {
  //           const nextArrows = document.querySelectorAll(".oi.oi-arrow-right");
  //           nextArrows.forEach((el) => el.click());
  //           const prevoiusarrows =
  //             document.querySelectorAll(".oi.oi-arrow-left");
  //           prevoiusarrows.forEach((el) => el.click());
  //           // sessionStorage.removeItem("lastJobcardId");
  //         }, 500);
  //         return true;
  //       },
  //       confirmLabel: _t("Yes"),
  //       cancelLabel: _t("No"),
  //     });

  //     if (!confirmed) revert();
  //   } else {
  //     this.dialogService.add(WarningDialog, {
  //       title: _t("⚠️ Jobcard Cannot Be Rescheduled"),
  //       message: `
  //         Jobcard: ${record.rawRecord.display_name},
  //         Technician: ${userName || "Unassigned"},
  //         Status: ${record.rawRecord.job_card_state || "Unknown"},
  //         Cannot be rescheduled. Only New or Scheduled jobcards can be moved.
  //     `,
  //     });

  //     revert();
  //     return;
  //   }
  // }

  // nov-05-2025
  async onEventDrop(info) {
    const { event, revert } = info;
    const newResource = event.getResources()[0];
    const recordId = event.id;
    console.log("recordId--------", recordId);
    const record = this.props.model.records[recordId];

    if (!newResource || !record) {
      revert();
      this.env.services.notification.add(
        _t("Cannot move event: Invalid resource or record"),
        { type: "danger" },
      );
      return;
    }

    const oldResources = event.getResources();
    const oldStart = event.start;
    const oldEnd = event.end;

    const newUserId =
      newResource.id === "unassigned" ? null : parseInt(newResource.id);

    if (newResource.id !== "unassigned" && isNaN(newUserId)) {
      revert();
      this.env.services.notification.add(
        _t("Cannot move event: Invalid user ID"),
        { type: "danger" },
      );
      return;
    }

    const currentTime = luxon.DateTime.now();
    const newStartTime = event.start
      ? luxon.DateTime.fromJSDate(event.start)
      : null;

    if (!newStartTime) {
      revert();
      this.env.services.notification.add(
        _t("Cannot move event: Invalid start date"),
        { type: "danger" },
      );
      return;
    }

    // Disallow Friday (5) and Saturday (6)
	// commented on August 16 2026 by Vijaya bhaskar because client asked friday also schedule it 
   /* const startWeekday = newStartTime.weekday;
    if (startWeekday === 5 ) {
      this.env.services.notification.add(
        _t("Cannot schedule on Friday."),
        { type: "danger" },
      );
      revert();
      return;
    }*/

    // Validate date based on scale
    const scale = this.props.model.scale;
    let isValidDate = false;
    if (scale === "day") {
      isValidDate = newStartTime > currentTime;
    } else if (["week", "month", "year"].includes(scale)) {
      isValidDate = newStartTime.startOf("day") >= currentTime.startOf("day");
    } else {
      isValidDate = newStartTime > currentTime;
    }
    if (!isValidDate) {
      revert();
      this.env.services.notification.add(
        _t("Cannot move event: The start date must be in the future."),
        { type: "danger" },
      );
      return;
    }

    const formatOdooDate = (date) => {
      if (!date) return null;
      return luxon.DateTime.fromJSDate(date)
        .minus({ hours: 3 })
        .toFormat("yyyy-MM-dd HH:mm:ss");
    };

    const stateCode = record.rawRecord.job_card_state_code;
    const userId = record.rawRecord.user_ids?.[0];

    const userName = this.userIdToName[userId] || "Unassigned";

    console.log("userState", userName);
    function toAsciiDigits(str) {
      const arabicDigits = "٠١٢٣٤٥٦٧٨٩";
      return str.replace(/[٠-٩]/g, (d) => arabicDigits.indexOf(d));
    }
    console.log("record-------------->", record);

    if (stateCode === "101" || stateCode === "102") {
      const updateData = {
        user_ids: newUserId ? [[6, 0, [newUserId]]] : [[5]],
      };
      if (newResource.id === "unassigned") {
        updateData.planned_date_begin = false;
        updateData.planned_date_end = false;
        updateData.job_card_state_code = 101;
        updateData.job_state = "";
        updateData.job_card_state = "New";
        updateData.technician_first_visit_id = null;
        updateData.technician_second_visit_id = null;
      } else {
        updateData.planned_date_begin = event.start
          ? toAsciiDigits(formatOdooDate(event.start))
          : toAsciiDigits(record.rawRecord.planned_date_begin);

        updateData.planned_date_end = event.end
          ? toAsciiDigits(formatOdooDate(event.end))
          : toAsciiDigits(record.rawRecord.planned_date_end);
        let technicianId = newResource.id;
        console.log("Technician ID:", technicianId);

        const result = await this.env.services.orm.read(
          "project.task", // model
          [parseInt(recordId)], // single record ID
          ["second_visit_technician_bool"], // fields to fetch
        );

        const secondVisitBool =
          result?.[0]?.second_visit_technician_bool ?? null;
        console.log("Second Visit Bool:", secondVisitBool);

        // Assign technician depending on secondVisitBool
        if (secondVisitBool) {
          // Second visit is true → assign to second_visit_technician_id
          updateData.technician_second_visit_id = technicianId
            ? parseInt(technicianId, 10)
            : false;
        } else {
          // First visit → assign to first_visit
          updateData.technician_first_visit_id = technicianId
            ? parseInt(technicianId, 10)
            : false;
        }

        console.log("Final updateData:", updateData);
      }

      console.log("updata", updateData);

      // Confirmation dialog
      // const confirmed = await this.env.services.dialog.add(ConfirmationDialog, {
      //   title: _t("Confirm Task Update"),
      //   body:
      //     newResource.id === "unassigned"
      //       ? _t("Are you sure you want to unassign this task?")
      //       : _t(
      //           `Are you sure you want to assign this task to ${
      //             newResource.title || "the user"
      //           }?`
      //         ),
      //   confirm: async () => {
      //     try {
      //       console.log("📤 Updating project.task:", {
      //         recordId: parseInt(recordId),
      //         updateData,
      //       });
      //       await this.env.services.orm.write(
      //         "project.task",
      //         [parseInt(recordId)],
      //         updateData
      //       );

      //       if (newResource.id === "unassigned") {
      //         const machineRecords = await this.env.services.orm.searchRead(
      //           "machine.repair.support",
      //           [["task_id.id", "=", parseInt(recordId, 10)]], // ensure numeric comparison
      //           ["id"]
      //         );

      //         if (machineRecords.length > 0) {
      //           // Collect IDs in an array
      //           const machineIds = machineRecords.map((rec) => rec.id);

      //           // 🔹 Log the data before update
      //           console.log("Updating machine.repair.support records:", {
      //             machineIds,
      //             service_request_state: updateData.job_card_state || null,
      //             service_request_state_code:
      //               updateData.job_card_state_code || null,
      //             user_id:
      //               newResource.id === "unassigned"
      //                 ? null
      //                 : parseInt(newResource.id),
      //             team_id: null,
      //             technician_appointment_date:
      //               updateData.planned_date_begin || null,
      //           });

      //           // Update the records
      //           await this.env.services.orm.write(
      //             "machine.repair.support",
      //             machineIds, // ✅ must be array of IDs
      //             {
      //               service_request_state: updateData.job_card_state || null,
      //               service_request_state_code:
      //                 updateData.job_card_state_code || null,
      //               user_id:
      //                 newResource.id === "unassigned"
      //                   ? null
      //                   : parseInt(newResource.id),
      //               team_id: null,
      //               technician_appointment_date:
      //                 updateData.planned_date_begin || null,
      //             }
      //           );
      //         }
      //       }

      //       event.setResources(newUserId ? [newUserId] : []);
      //       let message, type;
      //       if (newUserId && newUserId !== "unassigned") {
      //         message = _t("Technician has been assigned successfully");
      //         type = "success";
      //       } else {
      //         message = _t("♻️ Job card list refreshed after unassignment");
      //         type = "info";
      //       }

      //       // Show notification
      //       this.env.services.notification.add(message, { type });

      //       // Optional: timeline label
      //       const labelEl = document.createElement("div");
      //       labelEl.classList.add("gantt-label");
      //       labelEl.textContent = `Moved: Start ${
      //         event.start
      //           ? luxon.DateTime.fromJSDate(event.start).toFormat(
      //               "M/d/yyyy, h:mm a"
      //             )
      //           : "N/A"
      //       }`;
      //       labelEl.style.position = "absolute";
      //       labelEl.style.backgroundColor = "#ffffff";
      //       labelEl.style.padding = "2px 5px";
      //       labelEl.style.borderRadius = "3px";
      //       labelEl.style.zIndex = "1000";

      //       const timelineContainer = document.querySelector(".fc-timeline");
      //       if (timelineContainer) {
      //         const eventLeft = info.el.offsetLeft;
      //         labelEl.style.left = `${eventLeft}px`;
      //         labelEl.style.top = "0px";
      //         timelineContainer.appendChild(labelEl);
      //         setTimeout(() => labelEl.remove(), 5000);
      //       }

      //       await this.fetchAllUsersAndTasks();
      //       this.resources = await this.mapRecordsToResources();
      //       this.listProjectTasks();
      //       if (newResource.id === "unassigned") {
      //         // ✅ Notify JobcardList to refresh
      //         this.env.bus.trigger("jobcard-unassigned");
      //       } else {
      //         // Assigned task logic
      //         setTimeout(() => {
      //           const nextArrows =
      //             document.querySelectorAll(".oi.oi-arrow-right");
      //           nextArrows.forEach((el) => el.click());
      //           const previousArrows =
      //             document.querySelectorAll(".oi.oi-arrow-left");
      //           previousArrows.forEach((el) => el.click());
      //         }, 2000);
      //       }

      //       return true;
      //     } catch (error) {
      //       this.env.services.notification.add(
      //         _t(`Failed to move event: ${error.message || "Unknown error"}`),
      //         { type: "danger" }
      //       );
      //       return false;
      //     }
      //   },
      //   cancel: async () => {
      //     // Revert to old data
      //     event.setResources(oldResources);
      //     if (oldStart) event.setStart(oldStart);
      //     if (oldEnd) event.setEnd(oldEnd);
      //     setTimeout(() => {
      //       const nextArrows = document.querySelectorAll(".oi.oi-arrow-right");
      //       nextArrows.forEach((el) => el.click());
      //       const prevoiusarrows =
      //         document.querySelectorAll(".oi.oi-arrow-left");
      //       prevoiusarrows.forEach((el) => el.click());
      //       // sessionStorage.removeItem("lastJobcardId");
      //     }, 500);
      //     return true;
      //   },
      //   confirmLabel: _t("Yes"),
      //   cancelLabel: _t("No"),
      // });
      const confirmed = await this.env.services.dialog.add(ConfirmationDialog, {
        title: _t("Confirm Task Update"),
        body:
          newResource.id === "unassigned"
            ? _t("Are you sure you want to unassign this task?")
            : _t(
              `Are you sure you want to assign this task to ${newResource.title || "the user"
              }?`,
            ),
        confirm: async () => {
          try {
            console.log("📤 Updating project.task:", {
              recordId: parseInt(recordId),
              updateData,
            });

            // ✅ Update project.task
            await this.env.services.orm.write(
              "project.task",
              [parseInt(recordId)],
              updateData,
            );

            // 🔍 Find linked machine.repair.support
            const machineRecords = await this.env.services.orm.searchRead(
              "machine.repair.support",
              [["task_id.id", "=", parseInt(recordId, 10)]],
              ["id"],
            );

            if (machineRecords.length > 0) {
              const machineIds = machineRecords.map((rec) => rec.id);
              console.log("🔹 Found machine.repair.support IDs:", machineIds);

              let teamId = null;
              const technicianId = parseInt(newResource.id, 10);

              // ✅ Only fetch team if technician is assigned
              if (newResource.id !== "unassigned") {
                const machineTeam = await this.env.services.orm.searchRead(
                  "machine.support.team",
                  [["leader_id.id", "=", technicianId]],
                  ["id", "leader_id"],
                );

                if (machineTeam.length > 0) {
                  teamId = machineTeam[0].id;
                  console.log("✅ Found team for technician:", teamId);
                } else {
                  console.log(
                    "⚠️ No matching team found for technician:",
                    technicianId,
                  );
                }
              }

              // ✅ Prepare update values for machine.repair.support
              const supportUpdateVals = {
                service_request_state: updateData.job_card_state,
                service_request_state_code: updateData.job_card_state_code,
                user_id: newResource.id === "unassigned" ? null : technicianId,
                team_id: teamId || null,
                technician_appointment_date:
                  updateData.planned_date_begin || null,
              };

              console.log(
                "🔸 Updating machine.repair.support:",
                supportUpdateVals,
              );

              // ✅ Write updates
              await this.env.services.orm.write(
                "machine.repair.support",
                machineIds,
                supportUpdateVals,
              );
            }

            // 🔔 Notify user
            event.setResources(newUserId ? [newUserId] : []);
            const message =
              newUserId && newUserId !== "unassigned"
                ? _t("Technician has been assigned successfully")
                : _t("♻️ Job card list refreshed after unassignment");
            const type =
              newUserId && newUserId !== "unassigned" ? "success" : "info";
            this.env.services.notification.add(message, { type });

            // 🔄 Refresh view and trigger UI updates
            await this.fetchAllUsersAndTasks();
            this.resources = await this.mapRecordsToResources();
            this.listProjectTasks();

            if (newResource.id === "unassigned") {
              this.env.bus.trigger("jobcard-unassigned");
            } else {
              setTimeout(() => {
                document
                  .querySelectorAll(".oi.oi-arrow-right")
                  .forEach((el) => el.click());
                document
                  .querySelectorAll(".oi.oi-arrow-left")
                  .forEach((el) => el.click());
              }, 500);
            }

            return true;
          } catch (error) {
            this.env.services.notification.add(
              _t(`Failed to move event: ${error.message || "Unknown error"}`),
              { type: "danger" },
            );
            return false;
          }
        },
        cancel: async () => {
          event.setResources(oldResources);
          if (oldStart) event.setStart(oldStart);
          if (oldEnd) event.setEnd(oldEnd);
          setTimeout(() => {
            document
              .querySelectorAll(".oi.oi-arrow-right")
              .forEach((el) => el.click());
            document
              .querySelectorAll(".oi.oi-arrow-left")
              .forEach((el) => el.click());
          }, 500);
          return true;
        },
        confirmLabel: _t("Yes"),
        cancelLabel: _t("No"),
      });

      if (!confirmed) revert();
    } else {
      this.dialogService.add(WarningDialog, {
        title: _t("⚠️ Jobcard Cannot Be Rescheduled"),
        // title: _t("⚠️ Jobcard Cannot Be Reassigned to \n Another Technician"),
        message: `
          Jobcard: ${record.rawRecord.display_name},
          Technician: ${userName || "Unassigned"},
          Status: ${record.rawRecord.job_card_state || "Unknown"},
          Cannot be rescheduled. Only New or Scheduled jobcards can be moved.
      `,
      });

      revert();
      return;
    }
  }

  onEventDragStart(info) {
    const { el, event } = info;
    // console.log(`Drag started for event ${event.id}`);
    el.classList.add("dragging-3d");
    console.log("Dragging started:", {
      element: el,
      direction: document.documentElement.getAttribute("dir"),
    });
  }

  onEventDragStop(info) {
    const { el, event } = info;
    el.classList.remove("dragging-3d");
  }

  async onWindowScroll(ev) {
    const div = ev.target;
    if (div.scrollTop + div.clientHeight >= div.scrollHeight) {
      if (await this.props.model._nextPage()) {
        setTimeout(() => this._showEventByPage(), 15000);
      }
    }
  }

  async _showEventByPage() {
    if (!this.fc.api) return;
    const workCenterIds = Object.keys(this.workCenterIdToName).map((id) =>
      parseInt(id),
    );
    for (const record of Object.values(this.props.model.currentPageRecord)) {
      if (
        (!workCenterIds.length ||
          workCenterIds.includes(record.rawRecord.work_center_id?.[0]) ||
          !record.rawRecord.work_center_id) &&
        ALLOWED_JOB_CARD_STATES.includes(record.rawRecord.job_card_state_code)
      ) {
        const eventRaw = await this.convertRecordToEvent(record);
        if (eventRaw) {
          this.fc.api.addEvent(eventRaw);
          if (!this.fc.api.getResourceById(eventRaw.resourceId)) {
            await this._createResourceByEvent(record);
          }
        }
      }
    }
    this.listProjectTasks();
  }

  cleanOptions(options) {
    const opts = [
      "plugins",
      "slotLabelFormat",
      "defaultView",
      "dayRender",
      "defaultDate",
      "dir",
      "eventLimit",
      "eventLimitClick",
      "eventLimitText",
      "eventRender",
      "header",
      "weekLabel",
      "weekNumbersWithinDays",
      "columnHeaderFormat",
      "columnHeaderHtml",
      "timeGridEventMinHeight",
    ];
    options.eventDidMount = this.onEventRender;
    opts.forEach((opt) => {
      delete options[opt];
    });
    if (this.props.model.meta.slotLabelFormat) {
      const slotLabelFormats = JSON.parse(
        this.props.model.meta.slotLabelFormat,
      );
      if (slotLabelFormats[this.props.model.scale] !== undefined) {
        options.slotLabelFormat = slotLabelFormats[this.props.model.scale];
      }
    }
    return options;
  }

  async mapRecordsToResources(
    items = null,
    forceUniqKey = false,
    forM2oMapping = false,
  ) {
    const resources = {};
    const resourceOrders = this._getResourceOrders();
    const columnFields = this.props.model.meta.columnFields || {};
    const fieldNames = Object.keys(columnFields);
    const workCenterIds = Object.keys(this.workCenterIdToName).map((id) =>
      parseInt(id),
    );
    const records =
      items ||
      Object.values(this.props.model.records).filter(
        (record) =>
          (!workCenterIds.length ||
            workCenterIds.includes(record.rawRecord.work_center_id?.[0]) ||
            !record.rawRecord.work_center_id) &&
          ALLOWED_JOB_CARD_STATES.includes(
            record.rawRecord.job_card_state_code,
          ),
      );

    records.forEach((record) => {
      if (record.rawRecord.job_card_state_code === "101") {
        record.rawRecord.job_card_state_code = "102"; // Auto-schedule
      }
    });

    for (const item of records) {
      let userIds = item.rawRecord.user_ids || [];
      const taskWorkCenterId = item.rawRecord.work_center_id?.[0] || null;

      const filteredUserIds = await Promise.all(
        userIds.map(async (userId) => {
          const user = await this.env.services.orm.read(
            "res.users",
            [userId],
            ["default_work_center_id"],
          );
          const userWorkCenterId = user?.[0]?.default_work_center_id || null;
          if (!userWorkCenterId) return false;
          const userWorkCenter = await this.env.services.orm.read(
            "work.center.location",
            userWorkCenterId,
            ["work_center_group_id"],
          );
          const userWorkCenterGroupId =
            userWorkCenter?.[0]?.work_center_group_id?.[0] || null;
          return (
            !this.currentWorkCenterGroupId ||
            userWorkCenterGroupId === this.currentWorkCenterGroupId
          );
        }),
      );

      userIds = userIds.filter((_, index) => filteredUserIds[index]);
      const uniqKeys =
        userIds.length === 0 ? ["unassigned"] : userIds.map(String);

      const matchingUsers = await Promise.all(
        userIds.map(async (userId) => {
          const user = await this.env.services.orm.read(
            "res.users",
            [userId],
            ["default_work_center_id"],
          );
          const userWorkCenterId =
            user?.[0]?.default_work_center_id?.[0] || null;
          if (!userWorkCenterId) return false;
          const userWorkCenter = await this.env.services.orm.read(
            "work.center.location",
            [userWorkCenterId],
            ["work_center_group_id"],
          );
          const userWorkCenterGroupId =
            userWorkCenter?.[0]?.work_center_group_id?.[0] || null;
          return (
            taskWorkCenterId === null ||
            userWorkCenterGroupId === this.currentWorkCenterGroupId
          );
        }),
      );

      const hasMatchingUser = matchingUsers.some(Boolean);
      if (!hasMatchingUser) {
        // console.log(
        //   `⛔ Skipping task ${item.id} — no matching user with correct work_center_group.`
        // );
        continue;
      }

      for (const uniqKey of uniqKeys) {
        const resourceItem = {
          id: uniqKey,
          recordId: item.id,
          postRenderFields: [],
          forceValues: {},
          extraResourceValues: {},
        };
        let title;
        if (uniqKey === "unassigned") {
          title = _t("Unassigned");
        } else {
          const userId = parseInt(uniqKey);
          const userName = this.userIdToName[userId];
          if (!userName) {
            // console.warn(`⚠️ Skipping user ID ${userId}, name not found.`);
            continue;
          }
          title = userName;
        }
        resourceItem.title = title;

        fieldNames.forEach((fieldName) => {
          let fieldTitle = item.rawRecord[fieldName];
          if (Array.isArray(item.rawRecord[fieldName])) {
            if (
              item.rawRecord[fieldName].every((val) => Number.isInteger(val))
            ) {
              fieldTitle = item.rawRecord[fieldName].toString();
            } else {
              fieldTitle =
                item.rawRecord[fieldName][item.rawRecord[fieldName].length - 1];
            }
          }

          const fieldObject = columnFields[fieldName];
          if (
            !fieldObject ||
            (!fieldObject.attrs?.gantt_group &&
              !fieldObject.attrs?.is_resource_group_field)
          ) {
            resourceItem.postRenderFields.push(fieldName);
            fieldTitle = this._getResourceMarkedTitle(fieldName, fieldTitle);
          }
          resourceItem[fieldName] = fieldTitle;
        });

        if (resourceOrders && resourceOrders.mapping) {
          for (const [resourceField, fieldName] of Object.entries(
            resourceOrders.mapping,
          )) {
            if (fieldNames.includes(fieldName)) {
              let resourceVal = item.rawRecord[fieldName];
              if (Array.isArray(resourceVal)) {
                resourceVal = resourceVal[resourceVal.length - 1];
              }
              resourceItem[resourceField] = resourceVal;
            }
          }
        }

        this.postUpdateResourceItem(resourceItem, item, fieldNames);
        resources[resourceItem.id] = resourceItem;
      }
    }

    // ✅ Fetch group ID for "Job Card Mobile User"
    const jobCardGroup = await this.env.services.orm.searchRead(
      "res.groups",
      [["name", "=", "Job Card Mobile User"]],
      ["id"],
    );
    const jobCardGroupId = jobCardGroup?.[0]?.id;
    if (!jobCardGroupId) {
      // console.warn("Group 'Job Card Mobile User' not found.");
      return [];
    }

    this.userIdToEmployeeNo = {}; // Init employee number map
    const allUserResources = [];

    for (const [userId, userName] of Object.entries(this.userIdToName)) {
      const user = await this.env.services.orm.read(
        "res.users",
        [parseInt(userId)],
        ["default_work_center_id", "groups_id"],
      );

      const groupIds = user?.[0]?.groups_id || [];
      if (!groupIds.includes(jobCardGroupId)) {
        continue; // ❌ Skip if not in target group
      }

      const userWorkCenterIds = user?.[0]?.default_work_center_id || [];
      let userWorkCenterGroupIdList = [];

      for (const wcId of userWorkCenterIds) {
        const userWorkCenter = await this.env.services.orm.read(
          "work.center.location",
          [wcId],
          ["work_center_group_id"],
        );
        const groupId = userWorkCenter?.[0]?.work_center_group_id?.[0];
        if (groupId) {
          userWorkCenterGroupIdList.push(groupId);
        }
      }

      const employee = await this.env.services.orm.searchRead(
        "hr.employee",
        [["user_id", "=", parseInt(userId)]],
        ["employee_no"],
      );
      const employeeNo = employee?.[0]?.employee_no || null;
      this.userIdToEmployeeNo[userId] = employeeNo;

      const shouldInclude =
        !this.currentWorkCenterGroupId ||
        userWorkCenterGroupIdList.some((id) =>
          this.currentWorkCenterGroupId.includes(id),
        );

      if (shouldInclude) {
        allUserResources.push({
          id: userId.toString(),
          title: `${userName}${employeeNo ? " (" + employeeNo + ")" : ""}`,
          employee_no: employeeNo,
          postRenderFields: [],
          forceValues: {},
          extraResourceValues: {},
        });
      }
    }

    const extra = this.extraResources();
    const allResources = [...extra, ...allUserResources];
    // console.log("✅ Final Resources:", allResources);
    return allResources;
  }

  postUpdateResourceItem(resourceItem, item, fieldNames) { }

  extraResources() {
    return [
      {
        id: "unassigned",
        title: _t("Unassigned"),
        postRenderFields: [],
        forceValues: {},
        extraResourceValues: {},
      },
    ];
  }

  _getResourceOrders() {
    const resourceOrder = this.props.model.meta.resourceOrder;
    if (!resourceOrder) return {};
    const orderKey = [];
    const mapping = {};
    const fieldNames = Object.keys(this.props.model.meta.columnFields || {});
    const orderFields = resourceOrder.split(",");
    orderFields.forEach((orderField) => {
      const sortKF = orderField.trim().split(" ");
      const fieldName = sortKF[0].trim();
      const sortKey = sortKF[sortKF.length - 1].trim().toLowerCase();
      if (fieldName && fieldNames.includes(fieldName)) {
        let fname = fieldName;
        mapping[fname] = fieldName;
        if (sortKey === "desc") fname = "-" + fname;
        orderKey.push(fname);
      }
    });
    return { key: orderKey.join(","), mapping };
  }

  makeUpStr(str) {
    return str.replace(/[^a-zA-Z0-9]/g, "_");
  }

  _getResourceMarkedTitle(resourceId, title) {
    return this.makeUpStr(resourceId + MARKED_TITLE_SEPARATOR + title);
  }

  _getFieldNameFromMarkedTitle(markedTitle) {
    return markedTitle.split(MARKED_TITLE_SEPARATOR);
  }

  _getUniqueResourceIds(columnNames, item) {
    const uniqKeys = [];
    const m2o = {};
    const m2oMapping = {};
    for (const colname of columnNames) {
      if (
        this.props.model.meta.columnFields?.[colname]?.attrs?.m2o &&
        Array.isArray(item.rawRecord[colname]) &&
        item.rawRecord[colname].every((val) => Number.isInteger(val))
      ) {
        m2o[colname] = item.rawRecord[colname];
        break;
      }
    }
    if (Object.keys(m2o).length > 0) {
      Object.entries(m2o).forEach(([colname, vals]) => {
        for (const val of vals) {
          const keys = columnNames.map((columnName) => {
            if (colname === columnName) return val;
            else if (Array.isArray(item.rawRecord[columnName])) {
              return item.rawRecord[columnName].toString();
            }
            return item.rawRecord[columnName];
          });
          const uniqKey = keys.join("_");
          uniqKeys.push(uniqKey);
          m2oMapping[uniqKey] = {};
          m2oMapping[uniqKey][colname] = val;
        }
      });
    } else {
      let uniq = item.title;
      if (columnNames.length > 0) {
        const keys = columnNames.map((columnName) => {
          if (Array.isArray(item.rawRecord[columnName])) {
            if (
              this.props.model.meta.columnFields?.[columnName]?.type ===
              "many2one" &&
              item.rawRecord[columnName].length > 0
            ) {
              return item.rawRecord[columnName][0];
            }
            return item.rawRecord[columnName].toString();
          }
          return item.rawRecord[columnName];
        });
        uniq = keys.join("_");
      }
      uniqKeys.push(uniq);
    }
    return { uniqKeys, m2oMapping };
  }

  _getResourceAreaColumns() {
    return this.props.model.data.resourceAreaColumns || [];
  }

  fcResourceToRecord(resource) {
    if (!resource || !resource.id) {
      // console.warn("Invalid or missing resource object:", resource);
      return { resourceId: resource?.id || "default" };
    }

    if (!resource.extendedProps) {
      // console.warn("Resource missing extendedProps:", resource);
      return { resourceId: resource.id };
    }

    const recordId = resource.extendedProps.recordId;
    const originRecord = recordId ? this.props.model.records[recordId] : null;
    const columnFields = this.props.model.meta.columnFields || {};
    const fieldMapping = this.props.model.meta.fieldMapping || {};
    const fieldNames = Object.keys(columnFields);
    const DATE_FIELDS = ["date_start", "date_delay", "date_stop"];
    const exceptFieldMapping = Object.keys(fieldMapping).filter((fm) =>
      DATE_FIELDS.includes(fm),
    );
    let exceptFieldNames = Object.entries(fieldMapping).map(([fm, fn]) => {
      if (exceptFieldMapping.includes(fm)) return fn;
      return false;
    });
    exceptFieldNames = exceptFieldNames.filter((fn) => fn !== false);
    const resp = { resourceId: resource.id };

    if (!originRecord) {
      if (resource.extendedProps.extraResourceValues) {
        return {
          ...resource.extendedProps.extraResourceValues,
          resourceId: resource.id,
        };
      }
      return resp;
    }

    fieldNames.forEach((fieldName) => {
      if (exceptFieldNames.includes(fieldName)) return;
      const record = this._getRecordByForceValue(
        originRecord,
        resource.extendedProps.forceValues || {},
        fieldName,
      );
      const rawRecord = record.rawRecord;
      resp[fieldName] = rawRecord[fieldName];
      if (Array.isArray(rawRecord[fieldName])) {
        if (rawRecord[fieldName].every((val) => Number.isInteger(val))) {
          resp[fieldName] = rawRecord[fieldName];
        } else resp[fieldName] = rawRecord[fieldName][0];
      }
    });

    // console.log("Resource record:", resp);
    return resp;
  }

  fcEventToRecord(event) {
    const resp = this.superFcEventToRecord(event);
    const resourceData = this.fcResourceToRecord(event.resource);
    return Object.assign(resp, resourceData);
  }

  superFcEventToRecord(event) {
    const { id, allDay, date, start, end } = event;
    const res = {
      start: luxon.DateTime.fromJSDate(date || start),
      isAllDay: allDay,
    };
    if (end) {
      res.end = luxon.DateTime.fromJSDate(end);
      if (
        ["day", "week", "month", "year"].includes(this.props.model.scale) &&
        allDay
      ) {
        res.end = res.end.minus({ days: 1 });
      }
    }
    if (id) {
      const existingRecord = this.props.model.records[id];
      res.id = existingRecord.id;
    }
    return res;
  }

  superConvertRecordToEvent(record) {
    const allDay = record.isAllDay || record.endType === "date";
    if (!record.start || !record.end) {
      return null;
    }
    let startDate = record.start;
    let endDate = record.end;

    if (typeof startDate === "string") {
      startDate = luxon.DateTime.fromFormat(
        startDate,
        "yyyy-MM-dd HH:mm:ss",
      ).toISO();
    } else {
      startDate = startDate.toISO();
    }
    if (typeof endDate === "string") {
      endDate = luxon.DateTime.fromFormat(
        endDate,
        "yyyy-MM-dd HH:mm:ss",
      ).toISO();
    } else {
      endDate = endDate.toISO();
    }

    if (["day", "week", "month", "year"].includes(this.props.model.scale)) {
      if (
        record.isAllDay ||
        (allDay &&
          luxon.DateTime.fromISO(endDate).toMillis() !==
          luxon.DateTime.fromISO(endDate).startOf("day").toMillis())
      ) {
        endDate = luxon.DateTime.fromISO(endDate).plus({ days: 1 }).toISO();
      }
    }

    return {
      id: record.id,
      title: record.title || record.rawRecord.name || `Task ${record.id}`,
      start: startDate,
      end: endDate,
      allDay: allDay,
    };
  }
  async convertRecordToEvent(item) {
    const workCenterId = item.rawRecord.work_center_id?.[0] || null;
    const workCenterIds = Object.keys(this.workCenterIdToName).map(Number);

    // Skip tasks outside allowed work centers
    if (
      workCenterIds.length &&
      workCenterId &&
      !workCenterIds.includes(workCenterId)
    ) {
      return null;
    }

    let userIds = item.rawRecord.user_ids || [];

    // ✅ Filter users by matching current work center group
    const filteredUserIds = await Promise.all(
      userIds.map(async (userId) => {
        try {
          const [user] = await this.env.services.orm.read(
            "res.users",
            [userId],
            ["default_work_center_id"],
          );
          const wcId = user?.default_work_center_id?.[0];
          if (!wcId) return false;

          const [wc] = await this.env.services.orm.read(
            "work.center.location",
            [wcId],
            ["work_center_group_id"],
          );
          const groupId = wc?.work_center_group_id?.[0];
          return (
            !this.currentWorkCenterGroupId ||
            this.currentWorkCenterGroupId.includes(groupId)
          );
        } catch (error) {
          // console.warn(`⚠️ Failed to check user ${userId}:`, error);
          return false;
        }
      }),
    );

    userIds = userIds.filter((_, index) => filteredUserIds[index]);

    // 🧩 Fallback to unassigned if no valid users remain
    if (!userIds.length) {
      const fallback = this.superConvertRecordToEvent(item);
      if (!fallback) return null;

      fallback.title = this.props.model.meta.hideEventTitle
        ? ""
        : item.rawRecord?.[this.props.model.meta.eventTitleField] ||
        item.rawRecord.name ||
        `${item.title}`;
      fallback.resourceIds = ["unassigned"];
      return fallback;
    }
    const hasMatchingUser = await Promise.any(
      userIds.map(async (userId) => {
        try {
          const [user] = await this.env.services.orm.read(
            "res.users",
            [userId],
            ["default_work_center_id"],
          );
          const wcId = user?.default_work_center_id?.[0];
          if (!wcId) return false;

          const [wc] = await this.env.services.orm.read(
            "work.center.location",
            [wcId],
            ["work_center_group_id"],
          );
          const groupId = wc?.work_center_group_id?.[0];
          return (
            !workCenterId || this.currentWorkCenterGroupId.includes(groupId)
          );
        } catch {
          return false;
        }
      }),
    ).catch(() => false); // Promise.any fails if all reject/return false

    const resp = this.superConvertRecordToEvent(item);
    if (!resp) return null;

    if (this.props.model.meta.hideEventTitle) {
      resp.title = "";
    } else if (this.props.model.meta.eventTitleField && item.rawRecord) {
      resp.title =
        item.rawRecord[this.props.model.meta.eventTitleField] ||
        item.rawRecord.name ||
        `Task ${item.id}`;
    }

    resp.resourceIds = hasMatchingUser
      ? userIds.filter((id) => id in this.userIdToName).map(String)
      : ["unassigned"];

    if (!hasMatchingUser) {
      // console.log(
      //   `🟡 No matching users, assigning task ${item.id} to unassigned.`
      // );
    }

    // console.log(`✅ Final event for task ${item.id}:`, resp);
    return resp;
  }

  async _createResourceByEvent(item, uniqKey = false, m2oMapping = false) {
    const workCenterId = item.rawRecord.work_center_id?.[0] || null;
    const workCenterIds = Object.keys(this.workCenterIdToName).map((id) =>
      parseInt(id),
    );
    let workCenterGroupId = null;
    if (workCenterId) {
      const workCenter = await this.env.services.orm.read(
        "work.center.location",
        [workCenterId],
        ["work_center_group_id"],
      );
      workCenterGroupId = workCenter?.[0]?.work_center_group_id?.[0] || null;
    }

    if (
      workCenterIds.length &&
      !workCenterIds.includes(workCenterId) &&
      workCenterId
    ) {
      return;
    }

    if (!item.rawRecord.job_card_state_code) {
      return;
    }

    const resources = await this.mapRecordsToResources(
      [item],
      uniqKey ? [uniqKey] : false,
      m2oMapping,
    );
    const resourceObj = resources[0];
    if (resourceObj) {
      this.fc.api.addResource(resourceObj, true);
    }
  }

  _getRecordByForceValue(record, forceValues, fieldName) {
    const record2 = Object.assign({}, record);
    if (forceValues[fieldName]) {
      record2.rawRecord = record ? Object.assign({}, record.rawRecord) : {};
      if (forceValues[fieldName] !== record2.rawRecord[fieldName]) {
        record2.rawRecord[fieldName] = forceValues[fieldName];
      }
    }
    // console.log("record2", record2);
    return record2;
  }

  //  onResourceLabelContent(args) {
  //    const minHeight = this.props.model.meta.minResourceHeight || "37px";
  //    const divEl = document.createElement("div");
  //    divEl.style.minHeight = minHeight;
  //
  //    const resourceId = args.resource.id;
  //    // 10/07/2025
  //    const resourceEmpId = args.resource.extendedProps.employee_no;
  //
  //    let label;
  //    if (resourceId === "unassigned") {
  //      label = _t("Unassigned");
  //    } else {
  //      const userId = parseInt(resourceId);
  //
  //      const userName = this.userIdToName[userId];
  //
  //      // oct - 16 - 2025;
  //      const workCenterIds = this.userIdToWorkCenterId[userId];
  //      const workCenterName = Array.isArray(workCenterIds)
  //        ? workCenterIds
  //            .map((id) => this.workCenterIdToName[id] || `Work Center ${id}`)
  //            .join(", ")
  //        : workCenterIds
  //        ? this.workCenterIdToName[workCenterIds] ||
  //          `Work Center ${workCenterIds}`
  //        : "No Work Center";
  //
  //      const employeeNo = resourceEmpId; //10/07/2025
  //
  //      if (!userName) {
  //        label = `User ID ${userId} (${workCenterName})`;
  //      } else {
  //        label = `${
  //          employeeNo ? ` ${employeeNo}  - ` : ""
  //        }  ${userName} - (${workCenterName})`;
  //      }
  //    }
  //
  //    divEl.appendChild(document.createTextNode(label));
  //
  //    return { domNodes: [divEl] };
  //  }

  //  onResourceLabelContent(args) {
  //    const minHeight = this.props.model.meta.minResourceHeight || "37px";
  //    const divEl = document.createElement("div");
  //    divEl.style.minHeight = minHeight;
  //
  //    const resourceId = args.resource.id;
  //    const employeeNo = args.resource.extendedProps.employee_no;
  //
  //    let label;
  //
  //    // ---------------------------------------------
  //    // UNASSIGNED
  //    // ---------------------------------------------
  //    if (resourceId === "unassigned") {
  //        label = _t("Unassigned");
  //    } else {
  //        const userId = parseInt(resourceId);
  //        const userName = this.userIdToName[userId];
  //
  //        const workCenterIds = this.userIdToWorkCenterId[userId];
  //
  //        // -------- Work Center Name ----------
  //        const workCenterName = Array.isArray(workCenterIds)
  //            ? workCenterIds
  //                .map((id) => this.workCenterIdToName[id] || "")
  //                .filter(Boolean)
  //                .join(", ")
  //            : (workCenterIds ? this.workCenterIdToName[workCenterIds] : "");
  //
  //        // --------------------------------------------------------
  //        // 🔥 HIDE USER if project selected AND NO WORK CENTER found
  //        // --------------------------------------------------------
  //        const selectedProject = this.projectState?.project_id;
  //
  //        if (selectedProject && !workCenterName) {
  //            return { domNodes: [] }; // hide row completely
  //        }
  //
  //        // ---------------------------------------------
  //        // LABEL FORMATION
  //        // ---------------------------------------------
  //        if (!userName) {
  //            label = `User ID ${userId}`;
  //        } else {
  //            label =
  //                `${employeeNo ? employeeNo + " - " : ""}` +
  //                `${userName}` +
  //                `${workCenterName ? " (" + workCenterName + ")" : ""}`;
  //        }
  //    }
  //
  //    divEl.appendChild(document.createTextNode(label));
  //    return { domNodes: [divEl] };
  //}
  onResourceLabelContent(args) {
    const minHeight = this.props.model.meta.minResourceHeight || "37px";
    const divEl = document.createElement("div");
    divEl.style.minHeight = minHeight;

    const resourceId = args.resource.id;
    const employeeNo = args.resource.extendedProps.employee_no;

    let label;

    if (resourceId === "unassigned") {
      label = _t("Unassigned");
    } else {
      const userId = parseInt(resourceId);
      const userName = this.userIdToName[userId];
      const workCenterIds = this.userIdToWorkCenterId[userId];

      const workCenterName = Array.isArray(workCenterIds)
        ? workCenterIds
          .map((id) => this.workCenterIdToName[id] || "")
          .filter(Boolean)
          .join(", ")
        : workCenterIds
          ? this.workCenterIdToName[workCenterIds]
          : "";

      label =
        `${employeeNo ? employeeNo + " - " : ""}` +
        `${userName}` +
        `${workCenterName ? " (" + workCenterName + ")" : ""}`;
    }

    divEl.appendChild(document.createTextNode(label));
    return { domNodes: [divEl] };
  }

  async onResourceLabelDidMount({ el, resource }) {
    const $parentEle = $(el.parentElement);
    const extendedProps = resource.extendedProps || {};
    const fieldNames = extendedProps.postRenderFields || [];
    const self = this;

    const recordId = extendedProps.recordId;
    const promises = [];
    fieldNames.forEach((fieldName) => {
      const title = extendedProps[fieldName];
      const safeTitle = title ? String(title).replace(/['"]/g, "\\$&") : "";
      const resourceEle = $parentEle
        .find(`:contains('${safeTitle}')`)
        .filter(function () {
          return this.textContent === title;
        })
        .first();
      if (resourceEle.length > 0) {
        const record = self._getRecordByForceValue(
          self.props.model.records[recordId] || {},
          extendedProps.forceValues || {},
          fieldName,
        );
        const props = {
          record,
          model: self.props.model.meta,
          fieldName,
        };
        const app = new App(DomGanttModelResource, {
          env: self.env,
          dev: self.env.debug,
          templates,
          props,
          translatableAttributes: ["data-tooltip"],
          translateFn: _t,
        });
        resourceEle[0].innerHTML = "";
        promises.push(app.mount(resourceEle[0]));
        console.log(
          " promises.push(app.mount(resourceEle[0]));",
          promises.push(app.mount(resourceEle[0])),
        );
      }
    });
    await Promise.all(promises);
  }

  onEventRender(info) {
    const { el, event } = info;
    const record = this.props.model.records[event.id];
    const jobCardstatus = record?.rawRecord?.job_card_state || "Unknown";

    // Clean up any previously injected elements
    while (el.firstChild) el.removeChild(el.firstChild);

    el.dataset.eventId = event.id;
    el.classList.add("o_event", "py-0");

    // Assign color based on user
    let taskColor = "#ADD8E6";
    if (record) {
      const userIds = record.rawRecord.user_ids || [];
      if (userIds.length > 0) {
        const firstUserId = userIds[0];
        taskColor = this.userColorMap[firstUserId] || taskColor;
      }
      if (record.isHatched) el.classList.add("o_event_hatched");
      if (record.isStriked) el.classList.add("o_event_striked");
    }
    el.style.backgroundColor = taskColor;

    // Define job card status color
    const statusColorMap = {
      New: "#17a2b8",
      Scheduled: "#28a745",
      "Technician Accepted": "#ffc107",
      "Technician Rejected": "#dc3545",
      "Failed to attend call": "#6c757d",
      "Out of City": "#fd7e14",
      Rescheduled: "#20c997",
      "Customer Accepted": "#007bff",
      "Technician Started": "#6610f2",
      "Technician Reached": "#0d6efd",
      "Warranty Verification": "#6f42c1",
      "Inspection Started": "#fd7e14",
      "Quotation Provided": "#ffc107",
      "Job Started": "#20c997",
      "Payment Refused": "#dc3545",
      "Unit Pull Out": "#6c757d",
      "Unit Replaced": "#0d6efd",
      "Unit Returned": "#17a2b8",
      Pending: "#ffc107",
      "On Hold - Spare Parts Required": "#fd7e14",
      "Parts Ready": "#20c997",
      "Parts Received": "#0d6efd",
      "Ready to Invoice": "#6610f2",
    };
    const statusColor = statusColorMap[jobCardstatus] || "#6c757d";

    // Title + status container
    const container = document.createElement("div");
    container.classList.add("jobcard-info");
    container.style.cssText = `
    padding: 4px;
    text-align:left;
    color: white;
    font-size: 1.0em;
    line-height: 1em;
    font-weight: bold;
  `;

    const titleEl = document.createElement("div");
    titleEl.textContent = event.title;
    //  background-color: ${statusColor};
    const statusEl = document.createElement("div");
    statusEl.textContent = jobCardstatus;
    statusEl.style.cssText = `

    border-radius: 3px;
    margin-top: 3px;
    font-size: 0.75em;
    padding: 2px 4px;
    color:black;
    background-color: white;
    display: inline-block;
  `;

    container.appendChild(titleEl);
    container.appendChild(statusEl);
    el.appendChild(container);

    // Tooltip info
    if (record && record.rawRecord) {
      const start = event.start
        ? luxon.DateTime.fromJSDate(event.start).toFormat("dd MMM yyyy, h:mm a")
        : "N/A";
      const customerName = Array.isArray(record.rawRecord.partner_id)
        ? record.rawRecord.partner_id[1]
        : "Unknown";
      const userId = record.rawRecord.user_ids?.[0];
      const userName = this.userIdToName[userId] || "Unassigned";

      el.setAttribute(
        "title",
        `JobCard #: ${record.rawRecord.name || event.title || "Untitled"}\n` +
        `Technician: ${_t(userName)}\n` +
        `Customer: ${_t(customerName)}\n` +
        `Appointment: ${start}\n` +
        `Status: ${_t(jobCardstatus)}`,
      );
    }
  }
}

DomGanttCommonRenderer.components = {
  ...CalendarCommonRenderer.components,
  Popover: DomGanttCommonPopover,
  MyComponent,
  // JobcardList,
};
