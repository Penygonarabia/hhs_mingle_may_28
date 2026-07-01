#!/usr/bin/env python3
"""
json_to_ct_layout.py

Reads KS Dashboard Ninja JSON exports from 20260617_DrillDown_ListIView_Fixed/
and generates service_dashboards_ct/data/service_dashboard_layout.xml
with the correct grid_corners (positions) for every CT item.

This replaces the need for the SQL DB export step. The JSON files
ARE the source of truth for the current layout.

Usage:
    python3 scripts/json_to_ct_layout.py

Reads:   ~/Downloads/20260617_DrillDown_ListIView_Fixed/*.json
         service_dashboards_ct/data/legacy_service_boards.xml
         service_dashboards_ct/data/service_user_boards.xml
Writes:  service_dashboards_ct/data/service_dashboard_layout.xml
"""

import json
import os
import sys
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_FOLDER = os.path.expanduser(
    "~/Downloads/20260617_DrillDown_ListIView_Fixed"
)
LEGACY_XML = os.path.join(
    REPO, "service_dashboards_ct", "data", "legacy_service_boards.xml"
)
USER_XML = os.path.join(
    REPO, "service_dashboards_ct", "data", "service_user_boards.xml"
)
LAYOUT_XML = os.path.join(
    REPO, "service_dashboards_ct", "data", "service_dashboard_layout.xml"
)

CT_MODULE = "service_dashboards_ct"

# Board ordering in output XML (same as legacy_board_order in other scripts)
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

# ---------------------------------------------------------------------------
# Board name → xmlid mapping (JSON board name → CT module xmlid)
# ---------------------------------------------------------------------------
BOARD_NAME_TO_XMLID = {
    # Legacy boards
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
    # User boards
    "Service Analysis - CC Users":        "board_service_analysis_cc_users",
    "Service Analysis - CRD Users":       "board_service_analysis_crd_users",
    "Service Analysis - Parts Users":     "board_service_analysis_parts_users",
    "Service Analysis - Technicians":     "board_service_analysis_technicians",
}


# ---------------------------------------------------------------------------
# Parse XML to get ordered (item_xmlid, item_name) per board
# ---------------------------------------------------------------------------

def _get_field_text(record_elem, field_name):
    """Get the text content of a <field name="..."> inside a <record>."""
    for field in record_elem.findall("field"):
        if field.get("name") == field_name:
            return (field.text or "").strip()
    return ""


def _get_ref_short(ref_attr):
    """Strip module prefix from ref='module.xmlid' → 'xmlid'."""
    if ref_attr and "." in ref_attr:
        return ref_attr.split(".", 1)[1]
    return ref_attr or ""


def parse_xml_items(xml_path):
    """
    Returns:
        board_xmlid_by_name  {board_name -> short_xmlid}
        items_by_board       {board_short_xmlid -> [(item_short_xmlid, item_name), ...] in order}
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    board_xmlid_by_name = {}   # board name → xmlid
    items_by_board = {}        # board_xmlid → list of (item_xmlid, name)

    # Find <data> block(s)
    for data_block in root.iter("data"):
        for record in data_block.findall("record"):
            model = record.get("model", "")
            rec_id = record.get("id", "")

            if model == "ks_dashboard_ninja.board":
                name = _get_field_text(record, "name")
                if name:
                    board_xmlid_by_name[name] = rec_id

            elif model == "ks_dashboard_ninja.item":
                name = _get_field_text(record, "name")
                # Find board ref
                board_ref = ""
                for field in record.findall("field"):
                    if field.get("name") == "ks_dashboard_ninja_board_id":
                        ref_full = field.get("ref", "")
                        board_ref = _get_ref_short(ref_full)
                        break
                if board_ref and name:
                    items_by_board.setdefault(board_ref, []).append(
                        (rec_id, name)
                    )

    return board_xmlid_by_name, items_by_board


# ---------------------------------------------------------------------------
# Build name→xmlid lookup per board (handles duplicate names with order)
# ---------------------------------------------------------------------------

def build_item_lookup(items_by_board):
    """
    Returns:
        lookup  {board_xmlid -> {item_name -> deque([xmlid, ...])}}
    The deque handles duplicate names: first match consumes first entry.
    """
    from collections import deque
    lookup = {}
    for board_xid, item_list in items_by_board.items():
        name_map = {}
        for item_xid, item_name in item_list:
            name_map.setdefault(item_name, deque()).append(item_xid)
        lookup[board_xid] = name_map
    return lookup


# ---------------------------------------------------------------------------
# Read JSON exports
# ---------------------------------------------------------------------------

def load_json_positions(json_folder):
    """
    Returns:
        positions  {board_xmlid -> {item_xmlid -> {x,y,w,h}}}
        NOTE: item_xmlid is resolved from item name via XML lookup.
              This function returns positions keyed by item NAME;
              xmlid resolution is done after XML parsing.
    
    Actually returns:
        board_items  {board_xmlid -> [(item_name, grid_corners), ...] in JSON order}
    """
    board_items = {}  # board_xmlid -> [(item_name, grid_corners)]

    if not os.path.isdir(json_folder):
        sys.exit("ERROR: JSON folder not found: %s" % json_folder)

    for fname in sorted(os.listdir(json_folder)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(json_folder, fname)
        try:
            data = json.load(open(fpath, encoding="utf-8"))
        except Exception as e:
            print("WARN: Could not read %s: %s" % (fname, e))
            continue

        dashboard_list = data.get("ks_dashboard_data", [])
        if not dashboard_list:
            continue
        board_data = dashboard_list[0]
        board_name = board_data.get("name", "")
        board_xid = BOARD_NAME_TO_XMLID.get(board_name)
        if not board_xid:
            print("WARN: Unknown board name '%s' in %s — skipping" % (board_name, fname))
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
            pairs.append((name, {"x": int(gc["x"]), "y": int(gc["y"]),
                                  "w": int(gc["w"]), "h": int(gc["h"])}))
        board_items[board_xid] = pairs
        print("  Loaded %-35s → board %-40s (%d items)" % (
            fname, board_xid, len(pairs)))

    return board_items


# ---------------------------------------------------------------------------
# Match JSON items to xmlids
# ---------------------------------------------------------------------------

def resolve_positions(board_items, item_lookup):
    """
    Returns:
        resolved  {board_xmlid -> [(item_xmlid, grid_corners), ...]}
    """
    import copy
    resolved = {}
    total_matched = 0
    total_skipped = 0

    for board_xid, json_pairs in board_items.items():
        board_lookup = item_lookup.get(board_xid, {})
        # Deep copy the deques so we can consume them
        board_lookup_copy = {k: list(v) for k, v in board_lookup.items()}

        matched = []
        for item_name, gc in json_pairs:
            candidates = board_lookup_copy.get(item_name, [])
            if candidates:
                item_xid = candidates.pop(0)
                board_lookup_copy[item_name] = candidates
                matched.append((item_xid, gc))
                total_matched += 1
            else:
                print("  WARN: No xmlid found for item '%s' on board '%s' — skipped"
                      % (item_name, board_xid))
                total_skipped += 1

        resolved[board_xid] = matched

    print("\nResolution: %d matched, %d skipped" % (total_matched, total_skipped))
    return resolved


# ---------------------------------------------------------------------------
# Write layout XML
# ---------------------------------------------------------------------------

def _py_pos(p):
    return "{'x': %d, 'y': %d, 'w': %d, 'h': %d}" % (
        p["x"], p["y"], p["w"], p["h"]
    )


def write_layout_xml(resolved):
    """Write service_dashboard_layout.xml from resolved positions."""
    out = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<odoo>",
        '    <data noupdate="0">',
        "",
        "        <!-- Chart positions for every service_dashboards_ct board.",
        '             noupdate="0" so positions re-apply on every -u service_dashboards_ct;',
        "             the trailing <function/> call rebuilds the per-board",
        "             ks_gridstack_config so the UI actually renders in the",
        "             refreshed order.",
        "             Generated by scripts/json_to_ct_layout.py",
        "             from 20260617_DrillDown_ListIView_Fixed JSON exports.",
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
            for item_xid, gc in pairs:
                out.append(
                    '        <record id="%s" model="ks_dashboard_ninja.item">' % item_xid
                )
                out.append(
                    '            <field name="grid_corners">%s</field>' % _py_pos(gc)
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

    print("\nWrote %s" % LAYOUT_XML)
    print("  Items written: %d" % n_written)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Step 1: Parsing CT module XML for item xmlids ===")
    _, items_legacy = parse_xml_items(LEGACY_XML)
    board_names_user, items_user = parse_xml_items(USER_XML)

    # Merge both
    all_items = {}
    all_items.update(items_legacy)
    all_items.update(items_user)

    total_xml_items = sum(len(v) for v in all_items.values())
    print("  Boards found in XML: %d" % len(all_items))
    print("  Items found in XML : %d" % total_xml_items)

    item_lookup = build_item_lookup(all_items)

    print("\n=== Step 2: Loading JSON exports ===")
    board_items = load_json_positions(JSON_FOLDER)

    print("\n=== Step 3: Matching item names to xmlids ===")
    resolved = resolve_positions(board_items, item_lookup)

    print("\n=== Step 4: Writing service_dashboard_layout.xml ===")
    write_layout_xml(resolved)

    print("\nDone! Next steps:")
    print("  git diff service_dashboards_ct/data/service_dashboard_layout.xml")
    print("  git add service_dashboards_ct/data/service_dashboard_layout.xml")
    print("  git commit -m 'service_dashboards_ct: update layout from DrillDown_ListIView_Fixed exports'")


if __name__ == "__main__":
    main()
