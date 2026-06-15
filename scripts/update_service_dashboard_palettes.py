#!/usr/bin/env python3
"""
Apply Ninja Theme colour palettes to all chart items in the
"Service Dashboards" menu boards.

For rows 1-11: match items by name against the corresponding
Ninja Theme JSON, handle duplicate item names (e.g. "%") by
occurrence order within the board.

For rows 12-14 (CC Users / CRD Users / Technicians): no dedicated
Ninja JSON; apply type-based defaults consistent with Parts Users:
  ks_kpi          → moonrise
  everything else → default
"""

import json
import os
import sys
from collections import defaultdict

import psycopg2

NINJA_DIR = (
    "/Users/saravanan/Library/CloudStorage/"
    "OneDrive-Personal/Saravanan/1_Cielo_Digitals/Clients/HHS/"
    "1_Ninja_Dashboards/Services_Module/Ninja_Themes_Dashboards"
)

# Board name (as stored in DB) → Ninja Theme JSON filename.
# Rows 12-14 deliberately point at Parts Users so the name-counter
# fallback triggers (different item names → KPI=moonrise, chart=default).
BOARD_JSON_MAP = {
    "Technician Analysis - New":         "20260609Technician_Analysis.json",
    "Service Analysis (W) - New":        "20260609Sales_Analysis_W.json",
    "Service Analysis (UWC) - New":      "20260609Sales_Analysis_UWC.json",
    "Service Analysis - Parts Users":    "20260609Sales_Analysis_Parts_Users.json",
    "Service Analysis (Parts) - New":    "20260609Sales_Analysis_Parts.json",
    "Service Analysis - New":            "20260609Sales_Analysis.json",
    "Service Analysis (E) - New":        "20260609Sales_Analysis_E.json",
    "Service Analysis (CRD) - New":      "20260609Sales_Analysis_CRD.json",
    "Service Analysis (CC) - New":       "20260609Sales_Analysis_CC.json",
    "Service Analysis (C) - New":        "20260609Sales_Analysis_C.json",
    "Sales & Cost Analysis - New":       "20260609SalesCost_Analysis.json",
    # Rows 12-14: use Parts Users type-based fallback
    "Service Analysis - CC Users":       "20260609Sales_Analysis_Parts_Users.json",
    "Service Analysis - CRD Users":      "20260609Sales_Analysis_Parts_Users.json",
    "Service Analysis - Technicians":    "20260609Sales_Analysis_Parts_Users.json",
}

# Item types that are KPI widgets (use moonrise when falling back)
KPI_TYPES = {"ks_kpi"}


def load_json_palette(json_file):
    """Return ordered list of (name, item_type, palette) from a Ninja JSON."""
    path = os.path.join(NINJA_DIR, json_file)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    items = data["ks_dashboard_data"][0]["ks_item_data"]
    return [
        (
            item["name"],
            item.get("ks_dashboard_item_type", ""),
            item.get("ks_chart_item_color", "default"),
        )
        for item in items
    ]


def resolve_palette(palette_list, item_name, item_type, name_counters):
    """
    Match a DB item to its JSON counterpart by name (nth occurrence).
    Falls back to moonrise for KPIs and default for charts when no
    name match is found (handles rows 12-14 and any missing entries).
    """
    occurrence = name_counters[item_name]
    matches = [p for n, _, p in palette_list if n == item_name]
    if occurrence < len(matches):
        palette = matches[occurrence]
    elif matches:
        palette = matches[-1]
    else:
        palette = "moonrise" if item_type in KPI_TYPES else "default"
    name_counters[item_name] += 1
    return palette


def main():
    conn = psycopg2.connect(
        host="localhost", port=5434,
        dbname="dbcloud", user="odoo", password="odoo",
    )
    cur = conn.cursor()

    # Resolve the "Service Dashboards" menu ID
    cur.execute("""
        SELECT res_id FROM ir_model_data
        WHERE module = 'service_dashboards_ct'
          AND name   = 'service_dashboards_menu_root'
    """)
    row = cur.fetchone()
    if not row:
        sys.exit("ERROR: service_dashboards_menu_root xmlid not found in DB")
    menu_id = row[0]

    # All boards attached to that menu
    cur.execute("""
        SELECT id, name AS board_name
        FROM ks_dashboard_ninja_board
        WHERE ks_dashboard_top_menu_id = %s
        ORDER BY name
    """, (menu_id,))
    boards = cur.fetchall()
    print(f"Found {len(boards)} boards under 'Service Dashboards' (menu id={menu_id})\n")

    total_updated = 0

    for board_id, board_name in boards:
        json_file = BOARD_JSON_MAP.get(board_name)
        if not json_file:
            print(f"  SKIP (no JSON mapping): {board_name!r}")
            continue

        palette_list = load_json_palette(json_file)

        cur.execute("""
            SELECT id,
                   COALESCE(name->>'en_US', name::text) AS item_name,
                   ks_dashboard_item_type,
                   ks_chart_item_color
            FROM ks_dashboard_ninja_item
            WHERE ks_dashboard_ninja_board_id = %s
            ORDER BY id
        """, (board_id,))
        db_items = cur.fetchall()

        name_counters = defaultdict(int)
        board_updated = 0

        for item_id, item_name, item_type, current_palette in db_items:
            new_palette = resolve_palette(
                palette_list, item_name, item_type, name_counters
            )
            if new_palette != current_palette:
                cur.execute(
                    "UPDATE ks_dashboard_ninja_item "
                    "SET ks_chart_item_color = %s WHERE id = %s",
                    (new_palette, item_id),
                )
                board_updated += 1

        status = f"{board_updated}/{len(db_items)} items updated"
        print(f"  [{board_name}]  {status}")
        total_updated += board_updated

    conn.commit()
    print(f"\nDone — {total_updated} items updated across {len(boards)} boards.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
