/** @odoo-module **/
import { loadCSS, loadJS } from "@web/core/assets";
import {
  onMounted,
  onPatched,
  onWillStart,
  onWillUnmount,
  useComponent,
  useRef,
} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export function useDomGantt(refName, params) {
  const component = useComponent();
  const ref = useRef(refName);
  let instance = null;

  function boundParams() {
    const newParams = {};
    for (const key in params) {
      const value = params[key];
      newParams[key] =
        typeof value === "function" ? value.bind(component) : value;
    }
    // eslint-disable-next-line no-use-before-define
    const options = defaultParams();
    Object.assign(options, newParams);
    options.timeZone = "local";
    return options;
  }
  function defaultParams() {
    return {
      schedulerLicenseKey: "GPL-My-Project-Is-Open-Source",
      // Now: new Date(),
      editable: true,
      aspectRatio: 1.8,
      scrollTime: "00:00",
      headerToolbar: false,
      initialView: "resourceTimelineMonth",
      filterResourcesWithEvents: true,
      views: {
        // resourceTimelineDay: {
        //     buttonText: _t("Day"),
        //     slotDuration: {
        //         hours: 1,
        //     },
        // 	slotLabelContent: function (arg) {
        //         let hour = arg.date.getHours() % 12 || 12;
        //         let ampm = arg.date.getHours() < 12 ? "Am" : "Pm";
        //         return { html: `${hour} ${ampm}` };
        //     },

        // },

        // resourceTimelineDay: {
        //     buttonText: _t("Day"),
        //     slotDuration: { hours: 1 },
        //     slotMinTime: "08:00:00",
        //     slotMaxTime: "16:00:00",
        //     slotLabelContent: function (arg) {
        //         const hour = arg.date.getHours();
        //         const hour12 = hour % 12 === 0 ? 12 : hour % 12;
        //         const ampm = hour < 12 ? "AM" : "PM";
        //         return { html: `${hour12} ${ampm}` };
        //     },
        // },
        //08/09/2025
        resourceTimelineDay: {
          buttonText: _t("Day"),
          slotDuration: "00:30:00",
          slotLabelInterval: "00:30:00", // ✅ Add this!
          slotMinTime: "08:00:00",
          slotMaxTime: "18:00:00",
          slotLabelContent: function (arg) {
            const hour = arg.date.getHours();
            const minute = arg.date.getMinutes();
            const hour12 = hour % 12 === 0 ? 12 : hour % 12;
            const ampm = hour < 12 ? "AM" : "PM";
            return {
              html: `${hour12}.${minute.toString().padStart(2, "0")} ${ampm}`,
            };
          },
        },

        resourceTimelineWeek: {
          buttonText: _t("Week"),
          slotDuration: {
            hours: 24,
          },
          slotLabelFormat: [
            { weekday: "short", day: "numeric", month: "numeric" },
          ],
        },
        resourceTimelineMonth: {
          type: "resourceTimeline",
          buttonText: _t("Month"),
        },
        resourceTimelineYear: {
          buttonText: _t("Year"),
        },
      },
      navLinks: true,
      resourceAreaWidth: "25%",
      resourceAreaHeaderContent: "",
      resourceAreaColumns: [],
      resources: [],
      events: [],
    };
  }

  async function loadJsFiles() {
    const files = ["/dom_gantt_view/static/lib/fullcalendar/index.global.js"];
    for (const file of files) {
      await loadJS(file);
    }
  }
  async function loadCssFiles() {
    await Promise.all([].map((file) => loadCSS(file)));
  }

  onWillStart(() => Promise.all([loadJsFiles(), loadCssFiles()]));

  onMounted(() => {
    try {
      // eslint-disable-next-line no-undef
      instance = new FullCalendar2.Calendar(ref.el, boundParams());
      instance.render();
    } catch (e) {
      throw new Error(`Cannot instantiate FullCalendar\n${e.message}`);
    }
  });
  onPatched(() => {
    instance.refetchEvents();
  });
  onWillUnmount(() => {
    instance.destroy();
  });

  return {
    get api() {
      return instance;
    },
    get el() {
      return ref.el;
    },
  };
}
