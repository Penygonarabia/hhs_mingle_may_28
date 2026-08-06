/** @odoo-module **/

/*
 * Shared client-side UI-text translator for every PBI dashboard. Distinct
 * from the server-side _lang_for()/jsonb-column handling in
 * controllers/service_sql.py, which localizes *database values* (city/
 * customer names stored as translate=True jsonb) — this file only ever
 * touches static chrome: dashboard/card headings, KPI/chart names defined
 * in the Python board configs, legends, filter labels, header/footer text.
 * Never call t() on a value that came out of a database row (region/city/
 * status/customer/etc.) — those are already correctly localized server
 * side, and re-running them through this dict would either no-op (safe)
 * or, in a rare naming collision, silently mistranslate real data.
 *
 * Every dashboard.js registers its own board/KPI/chart-name strings via
 * addLabels() at module load time (once, when the asset bundle evaluates),
 * so LABELS ends up as one flat EN -> AR map shared across dashboards —
 * deliberate, not an oversight: generic chrome words ("Region", "Period",
 * "Total"...) only need one Arabic translation no matter which dashboard
 * renders them.
 */

import { session } from "@web/session";

export function isArabicUI() {
  const lang = (session.user_context && session.user_context.lang) || "";
  return lang.toLowerCase().startsWith("ar");
}

// Chrome strings shared by two or more dashboards (filter bars, chart-lib
// tooltips/legends, generic drill-breadcrumb root). Dashboard-specific
// board/KPI/chart names are added by each dashboard.js via addLabels().
const LABELS = {
  // filters
  "Period": "الفترة",
  "From": "من",
  "To": "إلى",
  "Region": "المنطقة",
  "All Regions": "كل المناطق",
  "All": "الكل",
  "Franchise": "الامتياز",
  "Year": "السنة",
  "Month": "الشهر",
  "Customer Groups": "مجموعات العملاء",
  "Sales Type Group": "مجموعة نوع المبيعات",
  // date filter options (service/promoter/contract DATE_FILTER_OPTIONS)
  "This Year": "هذا العام",
  "This Month": "هذا الشهر",
  "This Week": "هذا الأسبوع",
  "Last Year": "العام الماضي",
  "Last Month": "الشهر الماضي",
  "Last Week": "الأسبوع الماضي",
  "Custom": "مخصص",
  // pbi_chart_lib.js literals
  "Total": "الإجمالي",
  "Share": "الحصة",
  "Contribution": "المساهمة",
  "Actual": "الفعلي",
  "Total / Closed": "الإجمالي / المغلق",
  // generic header/footer scaffolding
  "Source": "المصدر",
  "PBI Dashboards": "لوحات معلومات PBI",
  "live from": "مباشرة من",
  "Service Dashboards": "لوحات معلومات الخدمة",
  "Contract Dashboards": "لوحات معلومات العقود",
  "Promoter Dashboards": "لوحات معلومات المروجين",
};

export function addLabels(dict) {
  Object.assign(LABELS, dict);
}

export function t(enText) {
  if (enText == null || !isArabicUI()) return enText;
  const hit = LABELS[enText];
  return hit !== undefined ? hit : enText;
}

// Period labels (header "Source: ... · <periodLabel>") are pre-formatted
// date strings from the server (Python strftime, e.g. "July 2026" or
// "Jan 01, 2026 - Jan 31, 2026"), not a fixed vocabulary lookup like
// everything else in LABELS — translate just the month-name words in
// place instead of needing the server to ship a second Arabic string.
const MONTH_NAMES = {
  January: "يناير", February: "فبراير", March: "مارس", April: "أبريل",
  May: "مايو", June: "يونيو", July: "يوليو", August: "أغسطس",
  September: "سبتمبر", October: "أكتوبر", November: "نوفمبر", December: "ديسمبر",
  Jan: "يناير", Feb: "فبراير", Mar: "مارس", Apr: "أبريل",
  Jun: "يونيو", Jul: "يوليو", Aug: "أغسطس",
  Sep: "سبتمبر", Oct: "أكتوبر", Nov: "نوفمبر", Dec: "ديسمبر",
};
const MONTH_RE = new RegExp(`\\b(${Object.keys(MONTH_NAMES).join("|")})\\b`, "g");

export function tDate(enText) {
  if (enText == null || !isArabicUI()) return enText;
  return enText.replace(MONTH_RE, (m) => MONTH_NAMES[m]);
}
