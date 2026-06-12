"""Re-dump the live KS Dashboard Ninja boards owned by `service_dashboard`
back into the two module XML data files, so the XML stays a faithful snapshot
of the DB.

Run via Odoo shell from inside the container:

    docker exec -i cloud-web-1 odoo shell \
        -c /etc/odoo/odoo.conf --db_host db --db_user odoo --db_password odoo \
        -d dbcloud --no-http < scripts/dump_service_dashboards.py

The repo is bind-mounted at /mnt/extra-addons inside the container; the
script writes directly to:
  /mnt/extra-addons/service_dashboard/data/legacy_service_boards.xml
  /mnt/extra-addons/service_dashboard/data/service_user_boards.xml

`env` (the Odoo Environment) is provided by `odoo shell` and used as a global.
"""

import json
import os
from xml.sax.saxutils import escape as xml_escape


MODULE = "service_dashboards_ot"
TARGET_MODELS = (
    "ks_dashboard_ninja.board",
    "ks_dashboard_ninja.item",
    "ks_dashboard_ninja.item_action",
)

# Bind-mount paths inside the Odoo container.
LEGACY_XML = "/mnt/extra-addons/service_dashboard/data/legacy_service_boards.xml"
USER_XML = "/mnt/extra-addons/service_dashboard/data/service_user_boards.xml"
# Layout file: noupdate=0 so chart positions (grid_corners) refresh on every
# `-u service_dashboard`. Other fields stay in the noupdate=1 files above so
# UI-tweaked colours/icons/etc on deployed servers survive an upgrade.
LAYOUT_XML = "/mnt/extra-addons/service_dashboard/data/service_dashboard_layout.xml"

# Board order — controls the section ordering in each output file.
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

# Per-model field whitelist. Anything not listed here is never serialized.
# These are the fields the original module XML carried — derived from
# `grep '<field name=' service_dashboard/data/*.xml | sort -u` on the
# pre-dump commit. Add a new entry here if you add a new field to the boards
# via UI and want it captured.
WHITELIST = {
    "ks_dashboard_ninja.board": [
        "name",
        "ks_dashboard_menu_name",
        "ks_dashboard_top_menu_id",
        "ks_dashboard_default_template",
        "ks_date_filter_selection",
        "ks_dashboard_menu_sequence",
        "ks_dashboard_active",
    ],
    "ks_dashboard_ninja.item": [
        "name",
        "ks_dashboard_ninja_board_id",
        "ks_model_id",
        "ks_record_field",
        "ks_chart_relation_groupby",
        "ks_chart_relation_sub_groupby",
        "ks_chart_measure_field",
        "ks_chart_date_groupby",
        "ks_date_filter_field",
        "ks_dashboard_item_type",
        "ks_chart_type",
        "ks_record_count_type",
        "ks_chart_data_count_type",
        "ks_record_data_limit",
        "ks_record_limit",
        "ks_data_calculation_type",
        "data_source",
        "ks_date_filter_selection",
        "ks_date_filter_selection_2",
        "ks_layout",
        "ks_background_color",
        "ks_font_color",
        "ks_header_bg_color",
        "ks_default_icon",
        "ks_default_icon_color",
        "ks_icon_select",
        "ks_dashboard_item_theme",
        "ks_chart_item_color",
        "ks_data_label_type",
        "ks_data_format",
        "ks_precision_digits",
        "ks_show_data_value",
        "ks_hide_legend",
        "ks_bar_chart_stacked",
        "ks_sort_by_field",
        "ks_sort_by_order",
        "ks_custom_query",
        "ks_item_action_field",
        "ks_list_view_type",
        "ks_domain",
        # grid_corners is intentionally NOT here — it goes into the
        # noupdate=0 layout file so chart positions can be re-pushed on
        # every `-u service_dashboard`.
    ],
    "ks_dashboard_ninja.item_action": [
        "name",
        "ks_dashboard_item_id",
        "sequence",
        "ks_actions",
        "ks_action_view_type",
        "ks_action_model_id",
        "ks_action_domain",
        "ks_action_fields_list",
        "ks_action_group_list",
        "ks_action_field_id",
    ],
}


def _xmlid_map():
    """Return {(model, db_id): "module.xmlid"} across the whole DB so m2o /
    m2m references can be resolved back to xmlids regardless of source module."""
    cr = env.cr
    cr.execute(
        "SELECT model, res_id, module, name FROM ir_model_data "
        "WHERE res_id IS NOT NULL"
    )
    out = {}
    for model, res_id, module, name in cr.fetchall():
        out.setdefault((model, res_id), "%s.%s" % (module, name))
    return out


def _en_us(value):
    """For translatable jsonb fields, prefer en_US; fall back to first locale."""
    if isinstance(value, dict):
        if "en_US" in value:
            return value["en_US"]
        if value:
            return next(iter(value.values()))
        return ""
    return value


def _is_empty(field, value):
    """Skip if the value is empty — never compare to model defaults; the
    whitelist is the source of truth for what to dump."""
    if value is False or value is None or value == "":
        return True
    if field.type in ("many2one", "many2many", "one2many") and not value:
        return True
    return False


def _serialize_field(record, field_name, xmlid_map):
    """Return an XML <field> line or None if the field should be skipped."""
    field = record._fields.get(field_name)
    if field is None:
        return None
    if not field.store:
        return None

    try:
        raw = record[field_name]
    except Exception:
        return None

    # Translatable name lives in jsonb; the record-level attribute already
    # returns the active-lang string, but we want en_US deterministically.
    if field.translate and field_name == "name":
        env.cr.execute(
            "SELECT name FROM %s WHERE id=%%s" % record._table,
            (record.id,),
        )
        row = env.cr.fetchone()
        if row:
            raw = _en_us(row[0])

    if _is_empty(field, raw):
        return None

    if field.type == "many2one":
        target = field.comodel_name
        target_id = raw.id if hasattr(raw, "id") else raw
        ref = xmlid_map.get((target, target_id))
        if not ref:
            return ("            <!-- skipped m2o %s: id=%s on %s has no xmlid -->"
                    % (field_name, target_id, target))
        return '            <field name="%s" ref="%s"/>' % (field_name, ref)

    if field.type == "many2many":
        target = field.comodel_name
        ids = list(raw.ids) if hasattr(raw, "ids") else list(raw)
        refs = []
        missing = []
        for rid in ids:
            xid = xmlid_map.get((target, rid))
            if xid:
                refs.append("ref('%s')" % xid)
            else:
                missing.append(rid)
        if not refs:
            return None
        body = '            <field name="%s" eval="[(6,0,[%s])]"/>' % (
            field_name, ",".join(refs))
        if missing:
            body += " <!-- m2m %s missing xmlids: %s -->" % (
                field_name, ",".join(str(i) for i in missing))
        return body

    if field.type == "boolean":
        return '            <field name="%s" eval="True"/>' % field_name

    if field.type in ("integer", "float"):
        return '            <field name="%s">%s</field>' % (field_name, raw)

    # char / text / selection / json-string fields (grid_corners, ks_domain, ...)
    text = raw if isinstance(raw, str) else str(raw)
    return '            <field name="%s">%s</field>' % (field_name, xml_escape(text))


def _serialize_record(record, xmlid_map, xmlid_name):
    """Emit XML for a single record. `xmlid_name` is the short id (without
    the module prefix)."""
    lines = ['        <record id="%s" model="%s">' % (xmlid_name, record._name)]
    # Walk fields in the whitelist's declared order — preserves the visual
    # field ordering the original XML used.
    for fname in WHITELIST.get(record._name, []):
        line = _serialize_field(record, fname, xmlid_map)
        if line is not None:
            lines.append(line)
    lines.append("        </record>")
    return "\n".join(lines)


def _collect_module_records(xmlid_map):
    """Return:
        boards_by_xid:  {xmlid_short: board_record}
        items_by_board: {board_xid: [(item_record, item_xmlid_short), ...]}
        actions_by_item:{item_xid:  [(action_record, action_xmlid_short), ...]}
    Records without an xmlid in this module are dropped (we cannot stably
    reference them, and they were never module-managed)."""
    Data = env["ir.model.data"]
    rows = Data.search([
        ("module", "=", MODULE),
        ("model", "in", list(TARGET_MODELS)),
    ])
    boards_by_xid = {}
    items_by_board = {}
    actions_by_item = {}
    item_to_board_xid = {}
    for d in rows:
        rec = env[d.model].browse(d.res_id).exists()
        if not rec:
            continue
        short = d.name
        if d.model == "ks_dashboard_ninja.board":
            boards_by_xid[short] = rec
        elif d.model == "ks_dashboard_ninja.item":
            bid = rec.ks_dashboard_ninja_board_id.id
            bxid = xmlid_map.get(("ks_dashboard_ninja.board", bid), "")
            # Strip "<module>." prefix to get the short id.
            bxid_short = bxid.split(".", 1)[1] if "." in bxid else bxid
            items_by_board.setdefault(bxid_short, []).append((rec, short))
            item_to_board_xid[rec.id] = bxid_short
        elif d.model == "ks_dashboard_ninja.item_action":
            iid = rec.ks_dashboard_item_id.id
            ixid = xmlid_map.get(("ks_dashboard_ninja.item", iid), "")
            ixid_short = ixid.split(".", 1)[1] if "." in ixid else ixid
            actions_by_item.setdefault(ixid_short, []).append((rec, short))
    # Stable ordering within a board: items by id asc, actions by sequence then id.
    for bxid in items_by_board:
        items_by_board[bxid].sort(key=lambda t: t[0].id)
    for ixid in actions_by_item:
        actions_by_item[ixid].sort(
            key=lambda t: (getattr(t[0], "sequence", 0) or 0, t[0].id))
    return boards_by_xid, items_by_board, actions_by_item


def _board_block(board_xid, board, items, actions_by_item, xmlid_map,
                 include_divider=True):
    """Render a board + its items (each followed by its actions). The divider
    comment uses the board's DB id so the marker is stable across re-dumps."""
    chunks = []
    if include_divider:
        chunks.append("        <!-- ============ Board %s: %s ============ -->" %
                      (board.id, _en_us({"en_US": board.name}) or board.name))
    chunks.append(_serialize_record(board, xmlid_map, board_xid))
    for item_rec, item_xid in items:
        chunks.append("")
        chunks.append(_serialize_record(item_rec, xmlid_map, item_xid))
        for act_rec, act_xid in actions_by_item.get(item_xid, []):
            chunks.append(_serialize_record(act_rec, xmlid_map, act_xid))
    return "\n".join(chunks)


# ---------------------------------------------------------------------------
# Top-of-file header for service_user_boards.xml. Preserved verbatim across
# dumps so we don't lose the HYBRID-strategy doc block. Edit here if needed.
USER_HEADER = '''<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">

        <!-- ================================================================
             HYBRID model strategy:
               * Per-user STATUS-COUNT charts  -> dbmodel.task.message.log.analysis
                 (message-log matview). One row per status transition, attributed
                 to the user who made the change (user_id) + their role (user_role)
                 + region/city. This is the only source that knows *which user was
                 involved in each status* (creator -> New, coordinator -> Scheduled,
                 parts -> Customer Need Quote, technician -> Rescheduled, etc.).
               * HOURS / region SUM charts -> dbmodel.jobcards.analysis
                 (one row per task, so hours are not multiplied across the many
                 transition rows a task has).

             Field refs:
               message-log : service_dashboards_ot.field_dbmodel_task_message_log_analysis__*
                             (ptml_final_taskstatus, task_date, user_id, user_role,
                              city, user_name, status_transition)
               jobcards    : service_dashboards_ot.field_dbmodel_jobcards_analysis__*
                             (work_center_group_id, total_worked_hours, ...)
             ================================================================ -->
'''

LEGACY_HEADER = '''<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">

'''

FOOTER = '''
    </data>
</odoo>
'''


def main():
    xmlid_map = _xmlid_map()
    boards_by_xid, items_by_board, actions_by_item = _collect_module_records(xmlid_map)

    # --- legacy_service_boards.xml ----------------------------------------
    legacy_chunks = [LEGACY_HEADER]
    for bxid in LEGACY_BOARD_ORDER:
        board = boards_by_xid.get(bxid)
        if not board:
            print("WARN: legacy board missing: %s" % bxid)
            continue
        legacy_chunks.append(_board_block(
            bxid, board, items_by_board.get(bxid, []),
            actions_by_item, xmlid_map,
            include_divider=True,
        ))
        legacy_chunks.append("")
    legacy_chunks.append(FOOTER.lstrip("\n"))
    with open(LEGACY_XML, "w") as f:
        f.write("\n".join(legacy_chunks).rstrip() + "\n")
    print("Wrote %s" % LEGACY_XML)

    # --- service_user_boards.xml ------------------------------------------
    user_chunks = [USER_HEADER]
    for bxid in USER_BOARD_ORDER:
        board = boards_by_xid.get(bxid)
        if not board:
            print("WARN: user board missing: %s" % bxid)
            continue
        user_chunks.append(_board_block(
            bxid, board, items_by_board.get(bxid, []),
            actions_by_item, xmlid_map,
            include_divider=False,
        ))
        user_chunks.append("")
    user_chunks.append(FOOTER.lstrip("\n"))
    with open(USER_XML, "w") as f:
        f.write("\n".join(user_chunks).rstrip() + "\n")
    print("Wrote %s" % USER_XML)

    # --- service_dashboard_layout.xml (noupdate=0) ------------------------
    # Just the grid_corners for every item, plus a <function> call that
    # rebuilds each board's ks_gridstack_config from the freshly-applied
    # grid_corners. Loaded last so it runs AFTER the noupdate=1 files.
    layout_lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<odoo>",
        '    <data noupdate="0">',
        "",
        "        <!-- Chart positions for every service_dashboard board.",
        "             noupdate=\"0\" so positions re-apply on every -u service_dashboard;",
        "             the trailing <function/> call rebuilds the per-board",
        "             ks_gridstack_config so the UI actually renders in the",
        "             refreshed order. Regenerated by scripts/dump_service_dashboards.py.",
        "          -->",
        "",
    ]
    all_ordered_xids = []
    # Walk in the same board / item order the other files use, so this file
    # is deterministic and easy to diff.
    for board_order in (LEGACY_BOARD_ORDER, USER_BOARD_ORDER):
        for bxid in board_order:
            for item_rec, item_xid in items_by_board.get(bxid, []):
                gc = item_rec.grid_corners
                if not gc:
                    continue
                all_ordered_xids.append(item_xid)
                layout_lines.append(
                    '        <record id="%s" model="ks_dashboard_ninja.item">' % item_xid)
                layout_lines.append(
                    '            <field name="grid_corners">%s</field>' % xml_escape(gc))
                layout_lines.append("        </record>")
    layout_lines.extend([
        "",
        "        <!-- Refresh per-board gridstack_config from the grid_corners just",
        "             written above. Without this, the UI keeps rendering the old",
        "             layout even though the underlying positions changed. -->",
        '        <function model="ks_dashboard_ninja.board"'
        ' name="service_dashboard_rebuild_layouts"/>',
        "",
        "    </data>",
        "</odoo>",
        "",
    ])
    with open(LAYOUT_XML, "w") as f:
        f.write("\n".join(layout_lines))
    print("Wrote %s (%d items with grid_corners)" % (LAYOUT_XML, len(all_ordered_xids)))

    # Summary
    n_boards = len(boards_by_xid)
    n_items = sum(len(v) for v in items_by_board.values())
    n_actions = sum(len(v) for v in actions_by_item.values())
    print("Dumped: %d boards, %d items, %d item_actions" %
          (n_boards, n_items, n_actions))


main()
env.cr.commit()
