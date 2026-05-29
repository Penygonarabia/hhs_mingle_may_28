/** @odoo-module **/
// import { useState } from "@odoo/owl";

// export function useTaskStages() {
//   const state = useState({
//     stages: [],
//     loading: false,
//     error: null,
//   });

//   async function fetchTaskStages(orm, targetCode) {
//     state.loading = true;
//     state.error = null;
//     state.stages = [];
//     try {
//       const result = await orm.searchRead(
//         "project.task.type",
//         [["code", "=", String(targetCode)]],
//         ["id", "code", "name"]
//       );

//       if (result.length) {
//         state.stages = result;
//         console.log("✅ Task Stages Found:", result);
//       } else {
//         state.error = "❌ Task stage not found for this code.";
//         console.warn(state.error);
//       }
//     } catch (err) {
//       console.error("Error fetching task stages:", err);
//       state.error = err.message;
//     } finally {
//       state.loading = false;
//     }
//   }

//   return { state, fetchTaskStages };
// }

import { useState } from "@odoo/owl";

/**
 * Custom hook to fetch project task stages and task details.
 * @returns {Object} { state, fetchTaskStages }
 */
export function useTaskStages() {
  const state = useState({
    stages: [],
    taskInfo: null,
    loading: false,
    error: null,
  });

  /**
   * Fetch both task stages (by code) and task details (by id)
   * @param {Object} orm - The Odoo ORM service instance
   * @param {Number|String} targetCode - The task type code
   * @param {Number|String} jobcardIdInt - The jobcard/task ID
   */
  async function fetchTaskStages(orm, targetCode, jobcardIdInt) {
    state.loading = true;
    state.error = null;
    state.stages = [];
    state.taskInfo = null;

    try {
      // ✅ Fetch task stage by code
      const stageResult = await orm.searchRead(
        "project.task.type",
        [["code", "=", String(targetCode)]],
        ["id", "code", "name"]
      );

      // ✅ Fetch task info by ID
      const taskResult = await orm.searchRead(
        "project.task",
        [["id", "=", parseInt(jobcardIdInt)]],
        ["second_visit_technician_bool", "technician_first_visit_id"]
      );

      // ✅ Update reactive state
      if (stageResult.length) {
        state.stages = stageResult;
        console.log("✅ Task Stages Found:", stageResult);
      } else {
        state.error = "❌ Task stage not found for this code.";
        console.warn(state.error);
      }

      if (taskResult.length) {
        state.taskInfo = taskResult[0];
        console.log("🧩 Task Info Found:", taskResult[0]);
      }
    } catch (err) {
      console.error("❌ Error fetching task stages or info:", err);
      state.error = err.message;
    } finally {
      state.loading = false;
    }
  }

  return { state, fetchTaskStages };
}
