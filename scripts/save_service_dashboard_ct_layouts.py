#!/usr/bin/env python3
"""Snapshot the *current live* chart layout (order / position / size) of the
Service Dashboards CT boards back into the CT module's layout data file:

  service_dashboards_ct/data/service_dashboard_layout.xml
        -> grid_corners per item, keyed by xmlid, Python-dict format,
           plus the <function> gridstack-rebuild call (CT variant).

This is the CT-module counterpart of save_service_dashboard_layouts.py.

TWO MODES OF OPERATION
======================

MODE A — JSON exports (preferred, no DB access needed)
-------------------------------------------------------
Export dashboards from the Odoo UI (KS Dashboard Ninja → Export) and place
the JSON files in a folder. Then run:

    python3 scripts/save_service_dashboard_ct_layouts.py \\
        --json-folder ~/Downloads/20260617_DrillDown_ListIView_Fixed

The script reads each board's grid_corners from the exported JSON and maps
them back to the CT module xmlids (using the board/item names defined in
legacy_service_boards.xml and service_user_boards.xml).

MODE B — Live DB CSV export (fallback, requires DB access)
----------------------------------------------------------
Run the following SQL inside the Odoo container (or via psql on the host):

    docker exec -i cloud-web-1 psql \\
        -U odoo -d dbcloud \\
        -c "\\COPY (
              SELECT
                b.id   AS board_id,
                b.name AS board_name,
                b.ks_gridstack_config AS gridstack,
                imd.module || '.' || imd.name AS board_xmlid
              FROM ks_dashboard_ninja_board b
              JOIN ir_model_data imd
                ON imd.model = 'ks_dashboard_ninja.board'
               AND imd.res_id = b.id
              WHERE imd.module = 'service_dashboards_ct'
            ) TO '/tmp/sd_boards_ct.json' CSV HEADER"

    docker exec -i cloud-web-1 psql \\
        -U odoo -d dbcloud \\
        -c "\\COPY (
              SELECT
                it.id   AS item_id,
                it.ks_dashboard_ninja_board_id AS board_id,
                imd.module || '.' || imd.name AS item_xmlid
              FROM ks_dashboard_ninja_item it
              JOIN ir_model_data imd
                ON imd.model = 'ks_dashboard_ninja.item'
               AND imd.res_id = it.id
              WHERE imd.module = 'service_dashboards_ct'
            ) TO '/tmp/sd_items_ct.json' CSV HEADER"

    docker cp cloud-web-1:/tmp/sd_boards_ct.json /tmp/sd_boards_ct.json
    docker cp cloud-web-1:/tmp/sd_items_ct.json  /tmp/sd_items_ct.json

Then run without --json-folder:

    python3 scripts/save_service_dashboard_ct_layouts.py

USAGE
=====
    python3 scripts/save_service_dashboard_ct_layouts.py [--json-folder PATH]

    --json-folder PATH   Path to folder containing KS Dashboard Ninja JSON
                         exports. Defaults to DEFAULT_JSON_FOLDER below.
                         If no JSON folder is provided (or empty), falls back
                         to reading /tmp/sd_boards_ct.json + /tmp/sd_items_ct.json
                         (Mode B / DB CSV export).
"""

import argparse
import csv
import json
import os
import sys
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYOUT_XML = os.path.join(
    REPO, "service_dashboards_ct", "data", "service_dashboard_layout.xml"
)
LEGACY_XML = os.path.join(
    REPO, "service_dashboards_ct", "data", "legacy_service_boards.xml"
)
USER_XML = os.path.join(
    REPO, "service_dashboards_ct", "data", "service_user_boards.xml"
)

# Default JSON folder — update this when you export a new set of dashboards
DEFAULT_JSON_FOLDER = os.path.expanduser(
    "~/Downloads/20260617_DrillDown_ListIView_Fixed"
)

# DB CSV export paths (Mode B fallback)
BOARDS_CSV = "/tmp/sd_boards_ct.json"
ITEMS_CSV = "/tmp/sd_items_ct.json"

CT_MODULE = "service_dashboards_ct"

# ---------------------------------------------------------------------------
# Board ordering — controls section ordering in the output XML.
# ---------------------------------------------------------------------------
LEGACY_BOARD_ORDER = [
    "legacy_board_uwc",
    "legacy_board_c",
    "legacy_board_e",
    "legacy_board_w",
    "legacy_board_jcs",
    "legacy_board_cc",
    "legacy_board_crd",
    "legacy_board_sales_cost",
    "legacy_board_main",
    "legacy_board_parts",
    "legacy_board_technician",
]
USER_BOARD_ORDER = [
    "board_service_analysis_cc_users",
    "board_service_analysis_crd_users",
    "board_service_analysis_parts_users",
    "board_service_analysis_technicians",
]

# Board name (as exported by Odoo UI) → CT module xmlid
BOARD_NAME_TO_XMLID = {
    "Service Analysis (UWC) - New":       "legacy_board_uwc",
    "Service Analysis (C) - New":         "legacy_board_c",
    "Service Analysis (E) - New":         "legacy_board_e",
    "Service Analysis (W) - New":         "legacy_board_w",
    "Service Analysis (JCs) - New":       "legacy_board_jcs",
    "Service Analysis (CC) - New":        "legacy_board_cc",
    "Service Analysis (CRD) - New":       "legacy_board_crd",
    "Sales & Cost Analysis - New":        "legacy_board_sales_cost",
    "Service Analysis - New":             "legacy_board_main",
    "Service Analysis (Parts) - New":     "legacy_board_parts",
    "Technician Analysis - New":          "legacy_board_technician",
    "Service Analysis - CC Users":        "board_service_analysis_cc_users",
    "Service Analysis - CRD Users":       "board_service_analysis_crd_users",
    "Service Analysis - Parts Users":     "board_service_analysis_parts_users",
    "Service Analysis - Technicians":     "board_service_analysis_technicians",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _short_xmlid(full_xmlid, module=CT_MODULE):
    prefix = module + "."
    if full_xmlid and full_xmlid.startswith(prefix):
        return full_xmlid[len(prefix):]
    return full_xmlid


def _py_pos(p):
    return "{'x': %d, 'y': %d, 'w': %d, 'h': %d}" % (
        int(p["x"]), int(p["y"]), int(p["w"]), int(p["h"])
    )


# ---------------------------------------------------------------------------
# Parse CT module XML to get item xmlids per board (used by Mode A)
# ---------------------------------------------------------------------------

def _get_field_text(record_elem, field_name):
    for field in record_elem.findall("field"):
        if field.get("name") == field_name:
            return (field.text or "").strip()
    return ""


def _get_ref_short(ref_attr):
    if ref_attr and "." in ref_attr:
        return ref_attr.split(".", 1)[1]
    return ref_attr or ""


def parse_xml_items(xml_path):
    """Return items_by_board {board_xmlid -> [(item_xmlid, item_name), ...]}."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    items_by_board = {}
    for data_block in root.iter("data"):
        for record in data_block.findall("record"):
            if record.get("model") != "ks_dashboard_ninja.item":
                continue
            rec_id = record.get("id", "")
            name = _get_field_text(record, "name")
            board_ref = ""
            for field in record.findall("field"):
                if field.get("name") == "ks_dashboard_ninja_board_id":
                    board_ref = _get_ref_short(field.get("ref", ""))
                    break
            if board_ref and name:
                items_by_board.setdefault(board_ref, []).append((rec_id, name))
    return items_by_board


def parse_existing_layout_view_fields(xml_path):
    """Return {item_xmlid: (show_records, list_layout)} from layout XML.

    This allows DB CSV mode to refresh grid positions while preserving any
    list-view flags already curated in the layout file.
    """
    if not os.path.exists(xml_path):
        return {}
    try:
        tree = ET.parse(xml_path)
    except Exception:
        return {}

    existing = {}
    root = tree.getroot()
    for data_block in root.iter("data"):
        for record in data_block.findall("record"):
            if record.get("model") != "ks_dashboard_ninja.item":
                continue
            rec_id = record.get("id", "")
            show_records = False
            list_layout = ""
            for field in record.findall("field"):
                fname = field.get("name")
                if fname == "ks_show_records":
                    eval_val = (field.get("eval") or "").strip().lower()
                    text_val = (field.text or "").strip().lower()
                    show_records = eval_val == "true" or text_val == "true"
                elif fname == "ks_list_view_layout":
                    list_layout = (field.text or "").strip()
            existing[rec_id] = (show_records, list_layout)
    return existing


def build_item_lookup(items_by_board):
    """Return {board_xmlid -> {item_name -> [xmlid, ...]}} for name matching."""
    lookup = {}
    for board_xid, item_list in items_by_board.items():
        name_map = {}
        for item_xid, item_name in item_list:
            name_map.setdefault(item_name, []).append(item_xid)
        lookup[board_xid] = name_map
    return lookup


# ---------------------------------------------------------------------------
# MODE A: Load positions from JSON export files
# ---------------------------------------------------------------------------

def load_from_json_folder(json_folder):
    """
    Returns board_items {
        board_xmlid -> [
            (item_name, {x,y,w,h}, show_records, list_layout),
            ...
        ]
    }
    """
    board_items = {}
    if not os.path.isdir(json_folder):
        return None  # Signal folder not found

    files_found = 0
    for fname in sorted(os.listdir(json_folder)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(json_folder, fname)
        try:
            data = json.load(open(fpath, encoding="utf-8"))
        except Exception as e:
            print("  WARN: Could not read %s: %s" % (fname, e))
            continue

        dashboard_list = data.get("ks_dashboard_data", [])
        if not dashboard_list:
            continue
        board_data = dashboard_list[0]
        board_name = board_data.get("name", "")
        board_xid = BOARD_NAME_TO_XMLID.get(board_name)
        if not board_xid:
            print("  WARN: Unknown board name '%s' in %s — add it to BOARD_NAME_TO_XMLID"
                  % (board_name, fname))
            continue

        items = board_data.get("ks_item_data", [])
        pairs = []
        for it in items:
            name = it.get("name", "")
            gc = it.get("grid_corners")
            if not name or not isinstance(gc, dict):
                continue
            if not all(k in gc for k in ("x", "y", "w", "h")):
                continue
            show_records = bool(it.get("ks_show_records", False))
            list_layout = it.get("ks_list_view_layout") or ""
            pairs.append((
                name,
                {"x": int(gc["x"]), "y": int(gc["y"]),
                 "w": int(gc["w"]), "h": int(gc["h"])},
                show_records,
                list_layout,
            ))
        board_items[board_xid] = pairs
        files_found += 1
        print("  %-40s → %-40s (%d items)" % (fname, board_xid, len(pairs)))

    return board_items if files_found else None


def resolve_positions_from_json(board_items, item_lookup):
    """Match JSON item names to XML xmlids.

    Returns resolved {
        board_xmlid -> [(item_xmlid, gc, show_records, list_layout), ...]
    }
    """
    resolved = {}
    total_matched = total_skipped = 0
    for board_xid, json_tuples in board_items.items():
        board_lookup = {k: list(v) for k, v in item_lookup.get(board_xid, {}).items()}
        matched = []
        for item_name, gc, show_records, list_layout in json_tuples:
            candidates = board_lookup.get(item_name, [])
            if candidates:
                matched.append((candidates.pop(0), gc, show_records, list_layout))
                board_lookup[item_name] = candidates
                total_matched += 1
            else:
                print("  WARN: No xmlid for '%s' on board '%s'" % (item_name, board_xid))
                total_skipped += 1
        resolved[board_xid] = matched
    print("  Matched: %d  Skipped: %d" % (total_matched, total_skipped))
    return resolved


# ---------------------------------------------------------------------------
# MODE B: Load positions from DB CSV export files
# ---------------------------------------------------------------------------

def load_from_csv_exports():
    """
    Returns resolved {board_xmlid -> [(item_xmlid, {x,y,w,h}), ...]}
    Reads /tmp/sd_boards_ct.json and /tmp/sd_items_ct.json (CSV format).
    """
    if not os.path.exists(BOARDS_CSV) or not os.path.exists(ITEMS_CSV):
        return None  # Signal files not found

    board_gridstack = {}
    board_short_xid = {}
    with open(BOARDS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            bid = int(row["board_id"])
            board_short_xid[bid] = _short_xmlid(row["board_xmlid"])
            raw_gs = row.get("gridstack") or ""
            if raw_gs and raw_gs != "\\N":
                try:
                    board_gridstack[bid] = json.loads(raw_gs)
                except json.JSONDecodeError:
                    board_gridstack[bid] = {}
            else:
                board_gridstack[bid] = {}

    item_pos = {}
    item_xmlid = {}
    items_by_board = {}
    with open(ITEMS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            iid = int(row["item_id"])
            bid = int(row["board_id"])
            item_xmlid[iid] = _short_xmlid(row.get("item_xmlid") or "")
            gs = board_gridstack.get(bid, {})
            pos = gs.get(str(iid))
            if pos and isinstance(pos, dict) and "x" in pos:
                item_pos[iid] = {k: int(pos[k]) for k in ("x", "y", "w", "h")}
            bx = board_short_xid.get(bid, "")
            if bx:
                items_by_board.setdefault(bx, []).append(iid)

    for bx in items_by_board:
        items_by_board[bx].sort()

    resolved = {}
    total = skipped = 0
    for bx, ids in items_by_board.items():
        matched = []
        for iid in ids:
            pos = item_pos.get(iid)
            xid = item_xmlid.get(iid, "")
            if pos and xid:
                matched.append((xid, pos))
                total += 1
            else:
                skipped += 1
        resolved[bx] = matched
    print("  Matched: %d  Skipped: %d" % (total, skipped))
    return resolved


# ---------------------------------------------------------------------------
# Write layout XML
# ---------------------------------------------------------------------------

def write_layout_xml(resolved):
    existing_view_fields = parse_existing_layout_view_fields(LAYOUT_XML)
    out = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<odoo>",
        '    <data noupdate="0">',
        "",
        "        <!-- Chart positions + ListView fix for every service_dashboards_ct board.",
        '             noupdate="0" so all fields re-apply on every -u service_dashboards_ct;',
        "             the trailing <function/> call rebuilds the per-board",
        "             ks_gridstack_config so the UI actually renders in the",
        "             refreshed order.",
        "             Regenerated by scripts/save_service_dashboard_ct_layouts.py.",
        "             DrillDown + ListView fix sourced from 20260617_DrillDown_ListIView_Fixed.",
        "          -->",
        "",
    ]

    n_written = 0
    for board_order in (LEGACY_BOARD_ORDER, USER_BOARD_ORDER):
        for board_xid in board_order:
            pairs = resolved.get(board_xid, [])
            if not pairs:
                continue
            out.append("        <!-- Board: %s -->" % board_xid)
            for entry in pairs:
                # entry is (item_xid, gc, show_records, list_layout)
                # or (item_xid, gc) from Mode B (DB CSV) which lacks list-view data
                if len(entry) == 4:
                    item_xid, gc, show_records, list_layout = entry
                else:
                    item_xid, gc = entry
                    show_records, list_layout = existing_view_fields.get(
                        item_xid, (False, "")
                    )
                out.append(
                    '        <record id="%s" model="ks_dashboard_ninja.item">' % item_xid
                )
                out.append(
                    '            <field name="grid_corners">%s</field>' % _py_pos(gc)
                )
                if show_records:
                    out.append(
                        '            <field name="ks_show_records" eval="True"/>'
                    )
                if list_layout:
                    out.append(
                        '            <field name="ks_list_view_layout">%s</field>' % list_layout
                    )
                out.append("        </record>")
                n_written += 1
            out.append("")

    out += [
        "        <!-- Refresh per-board gridstack_config from the grid_corners just",
        "             written above. Without this, the UI keeps rendering the old",
        "             layout even though the underlying positions changed.",
        "             IMPORTANT: uses the CT module's own rebuild method. -->",
        '        <function model="ks_dashboard_ninja.board"'
        ' name="service_dashboard_ct_rebuild_layouts"/>',
        "",
        "    </data>",
        "</odoo>",
        "",
    ]

    with open(LAYOUT_XML, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    print("\nWrote: %s" % LAYOUT_XML)
    print("Items : %d" % n_written)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Snapshot CT dashboard chart positions into service_dashboard_layout.xml"
    )
    parser.add_argument(
        "--json-folder",
        metavar="PATH",
        default=DEFAULT_JSON_FOLDER,
        help="Folder containing KS Dashboard Ninja JSON exports (Mode A). "
             "Default: %s" % DEFAULT_JSON_FOLDER,
    )
    parser.add_argument(
        "--db-csv",
        action="store_true",
        help="Force Mode B (DB CSV export from /tmp/sd_boards_ct.json + /tmp/sd_items_ct.json)",
    )
    args = parser.parse_args()

    # Parse module XML to build name→xmlid maps (needed for Mode A)
    print("=== Parsing CT module XML for item xmlids ===")
    items_legacy = parse_xml_items(LEGACY_XML)
    items_user = parse_xml_items(USER_XML)
    all_items = {}
    all_items.update(items_legacy)
    all_items.update(items_user)
    total = sum(len(v) for v in all_items.values())
    print("  Boards: %d   Items: %d" % (len(all_items), total))
    item_lookup = build_item_lookup(all_items)

    # Choose mode
    resolved = None

    if not args.db_csv:
        print("\n=== Mode A: Loading from JSON folder ===")
        print("  Folder: %s" % args.json_folder)
        board_items = load_from_json_folder(args.json_folder)
        if board_items:
            print("  Resolving item names to xmlids...")
            resolved = resolve_positions_from_json(board_items, item_lookup)
        else:
            print("  No JSON files found in folder — falling back to Mode B")

    if resolved is None:
        print("\n=== Mode B: Loading from DB CSV exports ===")
        print("  Boards CSV: %s" % BOARDS_CSV)
        print("  Items  CSV: %s" % ITEMS_CSV)
        resolved = load_from_csv_exports()
        if resolved is None:
            sys.exit(
                "\nERROR: Neither JSON folder nor DB CSV files found.\n"
                "Either:\n"
                "  A) Export dashboards from Odoo UI and pass --json-folder PATH\n"
                "  B) Run the psql export queries documented at the top of this script\n"
                "     to generate /tmp/sd_boards_ct.json and /tmp/sd_items_ct.json"
            )

    print("\n=== Writing layout XML ===")
    write_layout_xml(resolved)

    print("\nNext steps:")
    print("  git diff service_dashboards_ct/data/service_dashboard_layout.xml")
    print("  git add service_dashboards_ct/data/service_dashboard_layout.xml")
    print("  git commit -m 'service_dashboards_ct: snapshot chart layout positions'")
    print("  # Then on server: odoo -u service_dashboards_ct -d dbcloud --stop-after-init")


if __name__ == "__main__":
    main()
