/** @odoo-module **/

/*
 * Every "PBI Dashboards > Contract Dashboards" board is rendered by the
 * SAME OWL component (contract_dashboard.js) — this list is only the set
 * of valid board keys to register as distinct ir.actions.client tags
 * (pbi_dashboards.contract_dashboard_<key>), one per menu item, so each
 * dashboard keeps its own independent access surface. The actual chart
 * configuration stays server-side only, in pbi_dashboards/controllers/
 * contract_config.py — the client never needs its own copy.
 */
export const CONTRACT_BOARD_KEYS = [
  'contract_analysis',
];
