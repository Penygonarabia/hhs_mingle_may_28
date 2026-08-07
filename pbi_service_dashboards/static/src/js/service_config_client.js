/** @odoo-module **/

/*
 * Every "PBI Dashboards > Service Dashboards" board is rendered by the
 * SAME OWL component (service_dashboard.js) — this list is only the set
 * of valid board keys to register as distinct ir.actions.client tags
 * (pbi_dashboards.service_dashboard_<key>), one per menu item, so each
 * dashboard keeps its own independent access surface. The actual chart
 * configuration (titles, domains, drill chains, ~130 items across 15
 * boards) stays server-side only, in pbi_dashboards/controllers/
 * service_config.py — the client never needs its own copy.
 */
export const BOARD_KEYS = [
  'service_analysis',
  'service_analysis_c',
  'service_analysis_e',
  'service_analysis_w',
  'service_analysis_uwc',
  'service_analysis_jcs',
  'service_analysis_cc',
  'service_analysis_crd',
  'service_analysis_parts',
  'technician_analysis',
  'sales_cost_analysis',
  'service_analysis_cc_users',
  'service_analysis_crd_users',
  'service_analysis_parts_users',
  'service_analysis_technicians',
];
