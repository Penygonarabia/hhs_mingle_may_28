//  async onEventDrop(info) {
//     const { event, revert } = info;
//     const newResource = event.getResources()[0];
//     const recordId = event.id;

//     const record = this.props.model.records[recordId];
//     if (!newResource || !record) {
//       revert();
//       this.env.services.notification.add(
//         _t("Cannot move event: Invalid resource or record"),
//         { type: "danger" }
//       );
//       return;
//     }

//     const oldResources = event.getResources();
//     const oldStart = event.start;
//     const oldEnd = event.end;

//     const newUserId =
//       newResource.id === "unassigned" ? null : parseInt(newResource.id);

//     if (newResource.id !== "unassigned" && isNaN(newUserId)) {
//       revert();
//       this.env.services.notification.add(
//         _t("Cannot move event: Invalid user ID"),
//         { type: "danger" }
//       );
//       return;
//     }

//     const currentTime = luxon.DateTime.now();
//     const newStartTime = event.start
//       ? luxon.DateTime.fromJSDate(event.start)
//       : null;

//     if (!newStartTime) {
//       revert();
//       this.env.services.notification.add(
//         _t("Cannot move event: Invalid start date"),
//         { type: "danger" }
//       );
//       return;
//     }

//     // Disallow Friday (5) and Saturday (6)
//     const startWeekday = newStartTime.weekday;
//     if (startWeekday === 5 || startWeekday === 6) {
//       this.env.services.notification.add(
//         _t("Cannot schedule on Friday or Saturday."),
//         { type: "danger" }
//       );
//       revert();
//       return;
//     }

//     // Validate date based on scale
//     const scale = this.props.model.scale;
//     const isValidDate = ["week", "month", "year"].includes(scale)
//       ? newStartTime.startOf("day") >= currentTime.startOf("day")
//       : newStartTime > currentTime;

//     if (!isValidDate) {
//       revert();
//       this.env.services.notification.add(
//         _t("Cannot move event: The start date must be in the future."),
//         { type: "danger" }
//       );
//       return;
//     }

//     const formatOdooDate = (date) => {
//       if (!date) return null;
//       return luxon.DateTime.fromJSDate(date)
//         .minus({ hours: 3 })
//         .toFormat("yyyy-MM-dd HH:mm:ss");
//     };

//      function toAsciiDigits(str) {
//       const arabicDigits = "٠١٢٣٤٥٦٧٨٩";
//       return str.replace(/[٠-٩]/g, (d) => arabicDigits.indexOf(d));
//     }
//     console.log("record-------------->", record);

//     const stateCode = record.rawRecord.job_card_state_code;
//     const userId = record.rawRecord.user_ids?.[0];
//     const userName = this.userIdToName[userId] || "Unassigned";

//     const dragAndDropJobStates = ["204", "133", "134"];

//     // MAIN ALLOWED CHECK
//     const isAllowed =
//       stateCode === "101" || // New
//       stateCode === "102" || // Scheduled
//       dragAndDropJobStates.includes(stateCode); // 204,133,134 → Reschedulable

//     if (!isAllowed) {
//       this.dialogService.add(WarningDialog, {
//         title: _t("⚠️ Jobcard Cannot Be Rescheduled"),
//         message: `
//                 Jobcard: ${record.rawRecord.display_name}
//                 Technician: ${userName}
//                 Status: ${record.rawRecord.job_card_state || "Unknown"}
//                 Cannot be rescheduled. Only New, Scheduled or allowed Rescheduled jobcards can be moved.
//             `,
//       });
//       revert();
//       return;
//     }

//     // ===============================
//     //   UPDATE LOGIC STARTS HERE
//     // ===============================

//     const updateData = {
//       user_ids: newUserId ? [[6, 0, [newUserId]]] : [[5]],
//     };

//     // Case 1: State 102 moved to unassigned → convert to NEW
//     if (stateCode === "102" && newResource.id === "unassigned") {
//       updateData.planned_date_begin = false;
//       updateData.planned_date_end = false;
//       updateData.job_card_state_code = 101;
//       updateData.job_state = "";
//       updateData.job_card_state = "New";
//       updateData.technician_first_visit_id = null;
//       updateData.technician_second_visit_id = null;
//     }

//     // Case 2: 204/133/134 or rescheduling with technician
//     else if (dragAndDropJobStates.includes(stateCode) || stateCode === "102") {
//       const stageResult = await this.orm.searchRead(
//         "project.task.type",
//         [["code", "=", String(record.rawRecord.job_card_state_code)]],
//         ["id", "code", "name"]
//       );

//       updateData.job_card_state_code = record.rawRecord.job_card_state_code;
//       updateData.job_card_state = record.rawRecord.job_card_state;
//       updateData.job_state = stageResult[0]?.id || false;

//      updateData.planned_date_begin = event.start
//           ? toAsciiDigits(formatOdooDate(event.start))
//           : toAsciiDigits(record.rawRecord.planned_date_begin);

//         updateData.planned_date_end = event.end
//           ? toAsciiDigits(formatOdooDate(event.end))
//           : toAsciiDigits(record.rawRecord.planned_date_end);

//       const technicianId =
//         newResource.id === "unassigned" ? false : parseInt(newResource.id);

//       const result = await this.env.services.orm.read(
//         "project.task",
//         [parseInt(recordId)],
//         ["second_visit_technician_bool"]
//       );

//       const secondVisitBool =
//         result?.[0]?.second_visit_technician_bool || false;

//       if (secondVisitBool) {
//         updateData.technician_second_visit_id = technicianId
//         ? parseInt(technicianId, 10)
//             : false;
//       } else {
//         updateData.technician_first_visit_id = technicianId
//          ? parseInt(technicianId, 10)
//             : false;
//       }
//     }

//     // ===============================
//     //   CONFIRMATION DIALOG
//     // ===============================

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
//           await this.env.services.orm.write(
//             "project.task",
//             [parseInt(recordId)],
//             updateData
//           );

//           // Update related machine.repair.support
//           const machineRecords = await this.env.services.orm.searchRead(
//             "machine.repair.support",
//             [["task_id.id", "=", parseInt(recordId)]],
//             ["id"]
//           );

//           if (machineRecords.length > 0) {
//             const machineIds = machineRecords.map((rec) => rec.id);

//             let teamId = null;
//             if (newResource.id !== "unassigned") {
//               const machineTeam = await this.env.services.orm.searchRead(
//                 "machine.support.team",
//                 [["leader_id.id", "=", parseInt(newResource.id)]],
//                 ["id"]
//               );
//               teamId = machineTeam?.[0]?.id || null;
//             }

//             const supportUpdateVals = {
//               service_request_state: updateData.job_card_state,
//               service_request_state_code: updateData.job_card_state_code,
//               user_id:
//                 newResource.id === "unassigned"
//                   ? null
//                   : parseInt(newResource.id),
//               team_id: teamId,
//               technician_appointment_date:
//                 updateData.planned_date_begin || null,
//             };

//             await this.env.services.orm.write(
//               "machine.repair.support",
//               machineIds,
//               supportUpdateVals
//             );
//           }

//           // Refresh UI
//           event.setResources(newUserId ? [newUserId] : []);
//                       const message =
//                         newUserId && newUserId !== "unassigned"
//                           ? _t("Technician has been assigned successfully")
//                           : _t("♻️ Job card list refreshed after unassignment");
//                       const type =
//                         newUserId && newUserId !== "unassigned" ? "success" : "info";
//                       this.env.services.notification.add(message, { type });

//           await this.fetchAllUsersAndTasks();
//           this.resources = await this.mapRecordsToResources();
//           this.listProjectTasks();
//            if (newResource.id === "unassigned" && dragAndDropJobStates) {
//               this.env.bus.trigger("jobcard-unassigned");
//               setTimeout(() => {
//                 document
//                   .querySelectorAll(".oi.oi-arrow-right")
//                   .forEach((el) => el.click());
//                 document
//                   .querySelectorAll(".oi.oi-arrow-left")
//                   .forEach((el) => el.click());
//               }, 500);
//             } else {
//               setTimeout(() => {
//                 document
//                   .querySelectorAll(".oi.oi-arrow-right")
//                   .forEach((el) => el.click());
//                 document
//                   .querySelectorAll(".oi.oi-arrow-left")
//                   .forEach((el) => el.click());
//               }, 500);
//             }

//           return true;
//         } catch (error) {
//           console.error(error);
//           this.env.services.notification.add(
//             _t(`Failed to move event: ${error.message}`),
//             { type: "danger" }
//           );
//           return false;
//         }
//       },
//       cancel: async () => {
//         event.setResources(oldResources);
//         if (oldStart) event.setStart(oldStart);
//         if (oldEnd) event.setEnd(oldEnd);
//         setTimeout(() => {
//             document
//               .querySelectorAll(".oi.oi-arrow-right")
//               .forEach((el) => el.click());
//             document
//               .querySelectorAll(".oi.oi-arrow-left")
//               .forEach((el) => el.click());
//           }, 500);
//         return true;
//       },
//     });

//     if (!confirmed) revert();
//   }
