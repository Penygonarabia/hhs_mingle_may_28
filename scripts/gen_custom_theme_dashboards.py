"""Generate custom_theme_service_boards.xml + layout from existing legacy boards.

Reads the source XML files, finds the 11 boards listed in BOARDS_TO_DUP, and
emits duplicates under the `ct_` prefix with chart-color-palette overrides
taken from the matching reference JSON dashboards.
"""
import json
import os
import re

REPO = "/Users/saravanan/Library/Mobile Documents/com~apple~CloudDocs/Saravanan/Cielo_Digital/Odoo/Applications/cloud"
REFS = "/Users/saravanan/Library/CloudStorage/OneDrive-Personal/Saravanan/1_Cielo_Digitals/Clients/HHS/1_Ninja_Dashboards/Services_Module/Ninja_Themes_Dashboards"
LEGACY_XML = f"{REPO}/service_dashboard/data/legacy_service_boards.xml"
USER_XML = f"{REPO}/service_dashboard/data/service_user_boards.xml"
LAYOUT_XML = f"{REPO}/service_dashboard/data/service_dashboard_layout.xml"

OUT_DATA = f"{REPO}/service_dashboard/data/custom_theme_service_boards.xml"
OUT_LAYOUT = f"{REPO}/service_dashboard/data/custom_theme_service_boards_layout.xml"

# board_xmlid -> reference JSON filename
BOARDS_TO_DUP = [
    ("legacy_board_sales_cost", "20260609SalesCost_Analysis.json", LEGACY_XML),
    ("legacy_board_main",       "20260609Sales_Analysis.json", LEGACY_XML),
    ("legacy_board_c",          "20260609Sales_Analysis_C.json", LEGACY_XML),
    ("legacy_board_cc",         "20260609Sales_Analysis_CC.json", LEGACY_XML),
    ("legacy_board_crd",        "20260609Sales_Analysis_CRD.json", LEGACY_XML),
    ("legacy_board_e",          "20260609Sales_Analysis_E.json", LEGACY_XML),
    ("legacy_board_parts",      "20260609Sales_Analysis_Parts.json", LEGACY_XML),
    ("legacy_board_uwc",        "20260609Sales_Analysis_UWC.json", LEGACY_XML),
    ("legacy_board_w",          "20260609Sales_Analysis_W.json", LEGACY_XML),
    ("legacy_board_technician", "20260609Technician_Analysis.json", LEGACY_XML),
    ("board_service_analysis_parts_users", "20260609Sales_Analysis_Parts_Users.json", USER_XML),
]

PREFIX = "ct_"


def load_ref_palettes(json_file):
    """Return ordered list of (item_name, item_type, palette)."""
    with open(os.path.join(REFS, json_file)) as f:
        d = json.load(f)
    data = d["ks_dashboard_data"]
    if isinstance(data, list):
        data = data[0]
    return [(it["name"], it["ks_dashboard_item_type"], it.get("ks_chart_item_color"))
            for it in data.get("ks_item_data", [])]


def parse_records(xml_path):
    """Yield (record_id, model, full_record_block) in document order."""
    with open(xml_path) as f:
        text = f.read()
    pattern = re.compile(
        r'<record\s+id="([^"]+)"\s+model="([^"]+)"[^>]*>.*?</record>', re.DOTALL)
    for m in pattern.finditer(text):
        yield m.group(1), m.group(2), m.group(0)


def parse_layout_corners(xml_path):
    """Return {item_xmlid: grid_corners_string}."""
    result = {}
    with open(xml_path) as f:
        text = f.read()
    pattern = re.compile(
        r'<record\s+id="([^"]+)"\s+model="ks_dashboard_ninja\.item"[^>]*>\s*'
        r'<field\s+name="grid_corners">([^<]+)</field>\s*</record>', re.DOTALL)
    for m in pattern.finditer(text):
        result[m.group(1)] = m.group(2)
    return result


def collect_board_records(xml_path, board_xmlid):
    """Return (board_record_block, [item_record_blocks_in_order],
                [item_xmlids_in_order], [action_record_blocks])."""
    records = list(parse_records(xml_path))
    board_block = None
    item_blocks = []
    item_xmlids = []
    action_blocks = []
    item_xmlid_set = set()
    for rid, model, block in records:
        if rid == board_xmlid and model == "ks_dashboard_ninja.board":
            board_block = block
            continue
        if board_block is None:
            continue  # not yet at our board
        if model == "ks_dashboard_ninja.board":
            break  # next board starts; we're done
        if model == "ks_dashboard_ninja.item":
            item_blocks.append(block)
            item_xmlids.append(rid)
            item_xmlid_set.add(rid)
        elif model == "ks_dashboard_ninja.item_action":
            # only keep actions whose ks_dashboard_item_id references one of our items
            m = re.search(r'name="ks_dashboard_item_id"\s+ref="service_dashboard\.([^"]+)"', block)
            if m and m.group(1) in item_xmlid_set:
                action_blocks.append(block)
    return board_block, item_blocks, item_xmlids, action_blocks


def get_field(block, field_name):
    m = re.search(
        rf'<field\s+name="{re.escape(field_name)}">([^<]*)</field>', block)
    return m.group(1) if m else None


def transform_block(block, id_remap):
    """Rewrite record id and any service_dashboard refs that appear in id_remap.
    Returns the new block string."""
    # Rewrite record id
    block = re.sub(
        r'(<record\s+id=")([^"]+)("\s+model=")',
        lambda m: m.group(1) + id_remap.get(m.group(2), m.group(2)) + m.group(3),
        block, count=1)
    # Rewrite ref="service_dashboards_ot.X" where X is in id_remap
    def _ref_sub(m):
        old = m.group(1)
        new = id_remap.get(old, old)
        return f'ref="service_dashboards_ot.{new}"'
    block = re.sub(r'ref="service_dashboard\.([^"]+)"', _ref_sub, block)
    return block


def apply_palette_override(item_block, palette):
    """Set ks_chart_item_color to palette."""
    if palette is None:
        return item_block
    if re.search(r'<field\s+name="ks_chart_item_color">', item_block):
        return re.sub(
            r'<field\s+name="ks_chart_item_color">[^<]*</field>',
            f'<field name="ks_chart_item_color">{palette}</field>',
            item_block, count=1)
    # If absent, append before </record>
    return item_block.replace(
        "</record>",
        f'            <field name="ks_chart_item_color">{palette}</field>\n        </record>',
        1)


def apply_menu_and_name_overrides(board_block, new_name, new_menu_xmlid, sequence):
    # name
    board_block = re.sub(
        r'(<field\s+name="name">)[^<]*(</field>)',
        rf'\g<1>{new_name}\g<2>', board_block, count=1)
    # ks_dashboard_menu_name
    board_block = re.sub(
        r'(<field\s+name="ks_dashboard_menu_name">)[^<]*(</field>)',
        rf'\g<1>{new_name}\g<2>', board_block, count=1)
    # top menu ref
    board_block = re.sub(
        r'(<field\s+name="ks_dashboard_top_menu_id"\s+ref=")[^"]+(")',
        rf'\g<1>{new_menu_xmlid}\g<2>', board_block, count=1)
    # sequence
    if re.search(r'<field\s+name="ks_dashboard_menu_sequence">', board_block):
        board_block = re.sub(
            r'(<field\s+name="ks_dashboard_menu_sequence">)[^<]*(</field>)',
            rf'\g<1>{sequence}\g<2>', board_block, count=1)
    return board_block


def main():
    # Load ref palettes
    ref_palettes = {}  # board_xmlid -> [(name, type, palette), ...]
    for bid, ref_file, _ in BOARDS_TO_DUP:
        ref_palettes[bid] = load_ref_palettes(ref_file)

    layout_corners = parse_layout_corners(LAYOUT_XML)

    new_menu = "service_dashboards_ot.service_dashboards_custom_theme_menu_root"

    out_lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<odoo>',
        '    <data noupdate="1">',
        '',
        '        <!-- Auto-generated: duplicates of Service Module dashboards with ',
        '             "Chart Color Palette" (ks_chart_item_color) updated to match the',
        '             reference JSON dashboards in',
        '             OneDrive/HHS/1_Ninja_Dashboards/Services_Module/Ninja_Themes_Dashboards.',
        '             All record IDs prefixed `ct_`. -->',
        '',
    ]

    layout_lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<odoo>',
        '    <data noupdate="0">',
        '',
        '        <!-- Grid positions for the Custom Theme Service Dashboards.',
        '             Mirrors the original boards layout from',
        '             service_dashboard_layout.xml. Rebuilds gridstack_config so',
        '             the duplicated boards render with the same chart layout. -->',
        '',
    ]

    seq = 10
    for bid, ref_file, src_xml in BOARDS_TO_DUP:
        board_block, item_blocks, item_xmlids, action_blocks = \
            collect_board_records(src_xml, bid)
        if board_block is None:
            raise RuntimeError(f"Board {bid} not found in {src_xml}")

        ref_items = ref_palettes[bid]
        # Pair items by type (in document order within each type group).
        # Repo and ref orderings can differ; this groups e.g. all bar charts
        # together and pairs the nth repo bar chart with the nth ref bar chart.
        ref_palette_by_type = {}
        for name, typ, pal in ref_items:
            ref_palette_by_type.setdefault(typ, []).append(pal)
        # Walk item_blocks, tracking per-type index.
        repo_type_idx = {}
        palette_for_item = []
        for block in item_blocks:
            typ = get_field(block, "ks_dashboard_item_type")
            idx = repo_type_idx.get(typ, 0)
            repo_type_idx[typ] = idx + 1
            queue = ref_palette_by_type.get(typ, [])
            if idx < len(queue):
                palette_for_item.append(queue[idx])
            elif queue:
                palette_for_item.append(queue[-1])  # fall back to last
            else:
                palette_for_item.append(None)
        if len(item_blocks) != len(ref_items):
            print(f"WARN: {bid} has {len(item_blocks)} items in repo vs {len(ref_items)} in ref; pairing by type+position")

        # id_remap covers board + items + actions
        id_remap = {bid: PREFIX + bid}
        action_xmlids = []
        for block in action_blocks:
            m = re.match(r'<record\s+id="([^"]+)"', block)
            action_xmlids.append(m.group(1))
        for xid in item_xmlids + action_xmlids:
            id_remap[xid] = PREFIX + xid

        # board name
        orig_name = get_field(board_block, "name") or bid
        # strip trailing " - New" if present, append " - Custom Theme"
        base_name = re.sub(r'\s*-\s*New\s*$', '', orig_name).strip()
        new_name = f"{base_name} - Custom Theme"

        new_board_block = transform_block(board_block, id_remap)
        new_board_block = apply_menu_and_name_overrides(
            new_board_block, new_name, new_menu, seq)
        seq += 2

        out_lines.append(f"        <!-- ==================== {new_name} ==================== -->")
        out_lines.append(_indent(new_board_block))
        out_lines.append('')

        for i, item_block in enumerate(item_blocks):
            new_block = transform_block(item_block, id_remap)
            palette = palette_for_item[i]
            new_block = apply_palette_override(new_block, palette)
            out_lines.append(_indent(new_block))
            out_lines.append('')

        for act_block in action_blocks:
            new_block = transform_block(act_block, id_remap)
            out_lines.append(_indent(new_block))
        out_lines.append('')

        # Layout (grid_corners) for new item xmlids
        for xid in item_xmlids:
            gc = layout_corners.get(xid)
            if not gc:
                continue
            new_xid = PREFIX + xid
            layout_lines.append(f'        <record id="{new_xid}" model="ks_dashboard_ninja.item">')
            layout_lines.append(f'            <field name="grid_corners">{gc}</field>')
            layout_lines.append('        </record>')
        layout_lines.append('')

    out_lines += [
        '    </data>',
        '</odoo>',
    ]
    layout_lines += [
        '        <!-- Rebuild per-board gridstack_config so the new boards',
        '             render in the intended layout. -->',
        '        <function model="ks_dashboard_ninja.board" name="service_dashboard_rebuild_layouts"/>',
        '',
        '    </data>',
        '</odoo>',
    ]

    with open(OUT_DATA, "w") as f:
        f.write("\n".join(out_lines) + "\n")
    with open(OUT_LAYOUT, "w") as f:
        f.write("\n".join(layout_lines) + "\n")
    print(f"Wrote {OUT_DATA}")
    print(f"Wrote {OUT_LAYOUT}")


def _indent(block):
    """Ensure block is indented with 8 spaces for the data section."""
    lines = block.split("\n")
    # Normalise: many source records already use 8-space indent; trust source.
    return "\n".join(("        " + l.lstrip()) if (l.strip().startswith("<record") or l.strip().startswith("</record")) else l
                     for l in lines)


if __name__ == "__main__":
    main()
