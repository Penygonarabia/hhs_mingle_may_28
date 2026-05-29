/** @odoo-module **/

// import { JobcardList } from "./JobcardList";
// import { patch } from "@web/core/utils/patch";
// import { SearchBar } from "@web/search/search_bar/search_bar";

// patch(JobcardList.prototype, {
//   /**
//    * Override loadJobCards to always include 'New' status filter
//    * and merge with search query (if any) and city filter.
//    */
//   async loadJobCards(searchQuery = "") {
//     try {
//       // Default status "New"
//       const domain = [["job_card_state_code", "in", ["101"]]];

//       // Merge search query if provided
//       if (searchQuery && searchQuery.trim()) {
//         domain.push(
//           "|",
//           ["name", "ilike", searchQuery.trim()],
//           ["customer_name", "ilike", searchQuery.trim()]
//         );
//       }

//       // Merge city filter
//       if (this.state.selectedCityId) {
//         domain.push([
//           "customer_city_id",
//           "=",
//           parseInt(this.state.selectedCityId),
//         ]);
//       }

//       const data = await this.orm.searchRead("project.task", domain, [
//         "id",
//         "name",
//         "customer_name",
//         "service_requested_datetime",
//         "job_card_state_code",
//         "job_state",
//         "job_card_state",
//         "customer_city_id",
//         "country_district_id",
//       ]);

//       this.state.jobCards = data.map((card) => {
//         const cityName = card.customer_city_id ? card.customer_city_id[1] : "";
//         const districtName = card.country_district_id
//           ? card.country_district_id[1]
//           : "";
//         let formattedDate = "";
//         if (card.service_requested_datetime) {
//           const d = new Date(card.service_requested_datetime.replace(" ", "T"));
//           const pad = (n) => n.toString().padStart(2, "0");
//           formattedDate = `${pad(d.getDate())}/${pad(
//             d.getMonth() + 1
//           )}/${d.getFullYear()} ${pad(d.getHours() + 3)}:${pad(
//             d.getMinutes()
//           )}:${pad(d.getSeconds())}`;
//         }
//         return {
//           ...card,
//           customer_city_name: cityName,
//           customer_district_name: districtName,
//           service_requested_datetime_formatted: formattedDate,
//         };
//       });
//     } catch (err) {
//       console.error("❌ Error loading job cards:", err);
//     }
//   },

//   /**
//    * Add search input handler to call patched loadJobCards with query
//    */
//   async onSearchInput(ev) {
//     const query = ev.target.value;
//     await this.loadJobCards(query);
//   },
// });
