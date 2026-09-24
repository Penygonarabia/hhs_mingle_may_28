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
import { useService, useBus } from "@web/core/utils/hooks"; // Added useBus
import { MyComponent } from "../custom/component";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { session } from "@web/session";

const MARKED_TITLE_SEPARATOR = "__DOMTTSEP__";
const SCALE_TO_FC_VIEW = {
  day: "resourceTimelineDay",
  week: "resourceTimelineWeek",
  month: "resourceTimelineMonth",
  year: "resourceTimelineYear",
};

const ALLOWED_JOB_CARD_STATES = [
  "101", "102", "103", "104", "105", "106", "107", "108", "109",
  "110", "111", "113", "114", "115", "116", "117", "118", "119",
  "120", "121", "122", "123", "125", "132", "133", "134", "152",
  "204", "156", "207",
];

const STORAGE_KEY_WC = "job_card_sch_selected_wc_id";
const STORAGE_KEY_USER = "job_card_sch_selected_user_id";
const STORAGE_KEY_POPULATED = "job_card_sch_is_populated";

export class DomGanttCommonRenderer extends CalendarCommonRenderer {
  get isSecondScreenScheduling() {
    return Boolean(this.env.searchModel?.context?.hide_jobcard_list);
  }

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
    this.getjobcardStatecode();
    this.dialogService = useService("dialog");
    this.notification = useService("notification");
    this.holidays = [];
    this.state = useState({ loading: true });

    this.projectState = useState({
      project_id: false,
      projects: [],
    });

    onWillStart(async () => {
      const user = (
        await this.orm.searchRead(
          "res.users",
          [["id", "=", this.user.userId]],
          ["project_ids"],
        )
      )[0];

      const projects = await this.orm.searchRead(
        "project.project",
        [["id", "in", user.project_ids]],
        ["id", "name"],
      );

      this.projectState.projects = projects;
      const contextProjId =
        this.env.searchModel?.context?.default_project_id ||
        this.env.searchModel?.context?.project_id;
      if (contextProjId && projects.some((p) => p.id === contextProjId)) {
        this.projectState.project_id = contextProjId;
      } else if (projects.length) {
        this.projectState.project_id = projects[0].id;
      }
      this.projectState.showProjectSelector = projects.length > 1;

      this.JobCardMobileUser = await this.user.hasGroup(
        "machine_repair_management.group_job_card_mobile_user",
      );
    });

    const isRTL = session.user_context.lang.startsWith("ar");

    onMounted(async () => {
      setTimeout(() => {
        this.env.bus.trigger("project-filter-updated", {
          project_id: this.projectState.project_id,
        });
      }, 300);

      const container = document.querySelector(".o_calendar_widget");
      if (container) {
        container.style.direction = isRTL ? "rtl" : "ltr";
      }

      this.state.loading = true;

      try {
        await new Promise((resolve) => browser.setTimeout(resolve, 1000));
        await this.fetchAllUsersAndTasks();
        this.listProjectTasks();
        this.scrollToTime();
        await this.loadHolidays();

        if (this.fc.api) {
          this.fc.api.refetchResources();
          this.fc.api.refetchEvents();
        }
      } catch (err) {
        console.error("Error loading calendar data:", err);
      } finally {
        this.state.loading = false;
      }
    });

    // Listen for Populate click from JobcardList
    if (this.env?.bus) {
      useBus(this.env.bus, "jobcard-filter-populated", async () => {
        await this.fetchAllUsersAndTasks();
        if (this.fc?.api) {
          this.fc.api.refetchResources();
          this.fc.api.refetchEvents();
        }
      });
    }

    onPatched(() => {
      this.listProjectTasks();
      if (this.fc.api) {
        this.fc.api.refetchResources();
        this.fc.api.refetchEvents();
      }
    });

    useEffect(() => {
      this.updateSize();
    });

    if (this.props.model.pagingEnable) {
      useExternalListener(window, "scroll", this.onWindowScroll, {
        passive: true,
      });
    }
  }

  onProjectChange(ev) {
    if (this.isSecondScreenScheduling && this.isHhsProject) {
      return;
    }
    this.projectState.project_id = parseInt(ev.target.value) || false;
    this.env.bus.trigger("project-filter-updated", {
      project_id: this.projectState.project_id,
    });

    this.fetchAllUsersAndTasks().then(() => {
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

      this.holidays = leaves;
      this.highlightHolidaySlots();
      return leaves;
    } catch (err) {
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

        const holiday = this.holidays.find((h) => {
          const from = new Date(h.date_from.replace(" ", "T"));
          let to = new Date(h.date_to.replace(" ", "T"));

          if (h.date_to.endsWith("24:00:00")) {
            to.setHours(23, 59, 59, 999);
          }

          return slotDate >= from && slotDate <= to;
        });

        if (holiday) {
          td.classList.add("holiday");
          td.style.backgroundColor = "#28a745";
          td.style.color = "#fff";

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

    applyHolidayStyles();
    const fcContainer = document.querySelector(".fc-timeline-body");
    if (!fcContainer) return;

    const observer = new MutationObserver(() => applyHolidayStyles());
    observer.observe(fcContainer, { childList: true, subtree: true });
  }

  async getjobcardStatecode() {
    const taskTypeRecords = await this.env.services.orm.searchRead(
      "project.task.type",
      [["code", "!=", false]],
      ["code", "name"],
    );

    this.jobCardStateCodes = taskTypeRecords.map((rec) => ({
      code: rec.code,
      name: rec.name,
    }));
    return this.jobCardStateCodes;
  }

  async fetchAllUsersAndTasks() {
    try {
      const isPopulated =
        this.isSecondScreenScheduling ||
        sessionStorage.getItem(STORAGE_KEY_POPULATED) === "true";

      // If Populate has not been clicked, only show Unassigned
      if (!isPopulated) {
        this.resources = [
          {
            id: "unassigned",
            title: _t("Unassigned"),
            extendedProps: {},
          },
        ];
        return;
      }

      const userId = this.env.services.user?.userId || this.env.user?.uid;
      const orm = this.env.services.orm;

      const jobCardGroup = await orm.searchRead(
        "res.groups",
        [["name", "=", "Job Card Mobile User"]],
        ["id"],
      );

      if (!jobCardGroup.length) return;
      const jobCardGroupId = jobCardGroup[0].id;

      const userDomain = [
        ["active", "=", true],
        ["share", "=", false],
      ];

      const users = await orm.searchRead("res.users", userDomain, [
        "id",
        "name",
        "login",
        "groups_id",
        "default_work_center_id",
        "project_ids",
      ]);

      let projectFilteredUsers = users;
      const selectedProject = this.projectState?.project_id;
      if (selectedProject) {
        projectFilteredUsers = users.filter((u) =>
          (u.project_ids || []).includes(selectedProject),
        );
      }

      let filteredUsers = projectFilteredUsers.filter((u) =>
        (u.groups_id || []).includes(jobCardGroupId),
      );

      // Only filter by sidebar Work Center & Technician on first screen (sidebar view)
      if (!this.isSecondScreenScheduling) {
        const selectedUserId = sessionStorage.getItem(STORAGE_KEY_USER);
        if (selectedUserId) {
          const userNum = parseInt(selectedUserId, 10);
          filteredUsers = filteredUsers.filter((u) => u.id === userNum);
        } else {
          const selectedWcId = sessionStorage.getItem(STORAGE_KEY_WC);
          if (selectedWcId) {
            const wcNum = parseInt(selectedWcId, 10);
            filteredUsers = filteredUsers.filter((u) => {
              const userWcs = (u.default_work_center_id || []).map((w) => (Array.isArray(w) ? w[0] : w));
              return userWcs.includes(wcNum);
            });
          }
        }
      }

      this.userIdToName = {};
      this.userColorMap = {};
      this.workCenterIdToName = {};
      this.userIdToWorkCenterId = {};

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
        this.userIdToName[user.id] = user.name;
        this.userIdToWorkCenterId[user.id] = user.default_work_center_id;
      });

      this.resources = filteredUsers
        .filter((u) => u && u.id && u.name)
        .map((u) => ({
          id: String(u.id),
          title: u.name,
          extendedProps: {
            work_center_id: u.default_work_center_id?.[0] || null,
          },
        }));

      // Unassigned is kept at the top
      this.resources.unshift({
        id: "unassigned",
        title: _t("Unassigned"),
        extendedProps: {},
      });
    } catch (err) {
      this.env.services.notification.add(_t("Error fetching assignees."), {
        type: "danger",
      });
      this.resources = [];
    }
  }

  listProjectTasks() {
    const workCenterIds = Object.keys(this.workCenterIdToName).map((id) =>
      parseInt(id),
    );
    const records = Object.values(this.props.model.records).filter(
      (record) =>
        (!workCenterIds.length ||
          workCenterIds.includes(record.rawRecord.work_center_id?.[0]) ||
          !record.rawRecord.work_center_id) &&
        ALLOWED_JOB_CARD_STATES.includes(record.rawRecord.job_card_state_code),
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
      filterResourcesWithEvents: false,
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
      select: this.onSelect.bind(this),
      eventDrop: this.onEventDrop.bind(this),
      eventDragStart: this.onEventDragStart.bind(this),
      eventDragStop: this.onEventDragStop.bind(this),
      eventContent: () => ({ domNodes: [] }),
      eventDidMount: this.onEventRender.bind(this),

      events: async (info, successCallback) => {
        const isPopulated =
          this.isSecondScreenScheduling ||
          sessionStorage.getItem(STORAGE_KEY_POPULATED) === "true";
        if (!isPopulated) {
          successCallback([]);
          return;
        }

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

    options_extra.resourceAreaWidth = this.props.model.meta.resourceWidth || "200px";

    if (this.props.model.meta.slotMinWidth) {
      options_extra.slotMinWidth = this.props.model.meta.slotMinWidth;
    }
    if (this.props.model.meta.resourceGroupField) {
      options_extra.resourceGroupField = this.props.model.meta.resourceGroupField;
    }
    if (this.props.model.meta.eventTimeFormatDigits) {
      options_extra.eventTimeFormat = {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      };
    }

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

  fcEventToRecord(event) {
    const res = super.fcEventToRecord(event);
    const resId = event.resource?.id || event.resourceId;
    if (resId) {
      res.resourceId = resId;
    }
    return res;
  }

  async onSelect(info) {
    if (info.jsEvent) {
      info.jsEvent.preventDefault();
    }
    if (this.popover) {
      this.popover.close();
    }
    const record = this.fcEventToRecord(info);
    const resId = info.resource?.id || info.resourceId;
    if (resId) {
      record.resourceId = resId;
    }
    await this.props.createRecord(record);
    if (this.fc?.api) {
      this.fc.api.unselect();
    }
  }

  async onEventDrop(info) {
    const { event, revert } = info;
    const newResource = event.getResources()[0];
    const recordId = event.id;
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

    function toAsciiDigits(str) {
      const arabicDigits = "٠١٢٣٤٥٦٧٨٩";
      return str.replace(/[٠-٩]/g, (d) => arabicDigits.indexOf(d));
    }

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

        const result = await this.env.services.orm.read(
          "project.task",
          [parseInt(recordId)],
          ["second_visit_technician_bool"],
        );

        const secondVisitBool = result?.[0]?.second_visit_technician_bool ?? null;

        if (secondVisitBool) {
          updateData.technician_second_visit_id = technicianId ? parseInt(technicianId, 10) : false;
        } else {
          updateData.technician_first_visit_id = technicianId ? parseInt(technicianId, 10) : false;
        }
      }

      const confirmed = await this.env.services.dialog.add(ConfirmationDialog, {
        title: _t("Confirm Task Update"),
        body:
          newResource.id === "unassigned"
            ? _t("Are you sure you want to unassign this task?")
            : _t(`Are you sure you want to assign this task to ${newResource.title || "the user"}?`),
        confirm: async () => {
          try {
            await this.env.services.orm.write(
              "project.task",
              [parseInt(recordId)],
              updateData,
            );

            const machineRecords = await this.env.services.orm.searchRead(
              "machine.repair.support",
              [["task_id.id", "=", parseInt(recordId, 10)]],
              ["id"],
            );

            if (machineRecords.length > 0) {
              const machineIds = machineRecords.map((rec) => rec.id);
              let teamId = null;
              const technicianId = parseInt(newResource.id, 10);

              if (newResource.id !== "unassigned") {
                const machineTeam = await this.env.services.orm.searchRead(
                  "machine.support.team",
                  [["leader_id.id", "=", technicianId]],
                  ["id", "leader_id"],
                );

                if (machineTeam.length > 0) {
                  teamId = machineTeam[0].id;
                }
              }

              const supportUpdateVals = {
                service_request_state: updateData.job_card_state,
                service_request_state_code: updateData.job_card_state_code,
                user_id: newResource.id === "unassigned" ? null : technicianId,
                team_id: teamId || null,
                technician_appointment_date: updateData.planned_date_begin || null,
              };

              await this.env.services.orm.write(
                "machine.repair.support",
                machineIds,
                supportUpdateVals,
              );
            }

            event.setResources(newUserId ? [newUserId] : []);
            const message =
              newUserId && newUserId !== "unassigned"
                ? _t("Technician has been assigned successfully")
                : _t("♻️ Job card list refreshed after unassignment");
            const type = newUserId && newUserId !== "unassigned" ? "success" : "info";
            this.env.services.notification.add(message, { type });

            await this.fetchAllUsersAndTasks();
            this.listProjectTasks();

            if (newResource.id === "unassigned") {
              this.env.bus.trigger("jobcard-unassigned");
            } else {
              setTimeout(() => {
                document.querySelectorAll(".oi.oi-arrow-right").forEach((el) => el.click());
                document.querySelectorAll(".oi.oi-arrow-left").forEach((el) => el.click());
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
            document.querySelectorAll(".oi.oi-arrow-right").forEach((el) => el.click());
            document.querySelectorAll(".oi.oi-arrow-left").forEach((el) => el.click());
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
        message: `
          Jobcard: ${record.rawRecord.display_name},
          Technician: ${userName || "Unassigned"},
          Status: ${record.rawRecord.job_card_state || "Unknown"},
          Cannot be rescheduled. Only New or Scheduled jobcards can be moved.
      `,
      });
      revert();
    }
  }

  onEventDragStart(info) {
    info.el.classList.add("dragging-3d");
  }

  onEventDragStop(info) {
    info.el.classList.remove("dragging-3d");
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
        }
      }
    }
    this.listProjectTasks();
  }

  cleanOptions(options) {
    const opts = [
      "plugins", "slotLabelFormat", "defaultView", "dayRender",
      "defaultDate", "dir", "eventLimit", "eventLimitClick",
      "eventLimitText", "eventRender", "header", "weekLabel",
      "weekNumbersWithinDays", "columnHeaderFormat", "columnHeaderHtml",
      "timeGridEventMinHeight",
    ];
    options.eventDidMount = this.onEventRender;
    opts.forEach((opt) => delete options[opt]);
    if (this.props.model.meta.slotLabelFormat) {
      const slotLabelFormats = JSON.parse(this.props.model.meta.slotLabelFormat);
      if (slotLabelFormats[this.props.model.scale] !== undefined) {
        options.slotLabelFormat = slotLabelFormats[this.props.model.scale];
      }
    }
    return options;
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

  _getResourceAreaColumns() {
    return this.props.model.data.resourceAreaColumns || [];
  }

  superConvertRecordToEvent(record) {
    const allDay = record.isAllDay || record.endType === "date";
    if (!record.start || !record.end) return null;

    let startDate = record.start;
    let endDate = record.end;

    if (typeof startDate === "string") {
      startDate = luxon.DateTime.fromFormat(startDate, "yyyy-MM-dd HH:mm:ss").toISO();
    } else {
      startDate = startDate.toISO();
    }
    if (typeof endDate === "string") {
      endDate = luxon.DateTime.fromFormat(endDate, "yyyy-MM-dd HH:mm:ss").toISO();
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

    if (workCenterIds.length && workCenterId && !workCenterIds.includes(workCenterId)) {
      return null;
    }

    let userIds = item.rawRecord.user_ids || [];
    if (!userIds.length) {
      const fallback = this.superConvertRecordToEvent(item);
      if (!fallback) return null;
      fallback.resourceIds = ["unassigned"];
      return fallback;
    }

    const resp = this.superConvertRecordToEvent(item);
    if (!resp) return null;

    resp.resourceIds = userIds.filter((id) => id in this.userIdToName).map(String);
    if (!resp.resourceIds.length) {
      resp.resourceIds = ["unassigned"];
    }

    return resp;
  }

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

  onEventRender(info) {
    const { el, event } = info;
    const record = this.props.model.records[event.id];
    const jobCardstatus = record?.rawRecord?.job_card_state || "Unknown";

    while (el.firstChild) el.removeChild(el.firstChild);

    el.dataset.eventId = event.id;
    el.classList.add("o_event", "py-0");

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
};