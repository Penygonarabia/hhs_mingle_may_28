"""Shared PowerPoint presentation layer for the Sales Analysis decks.

Pure presentation: every method here turns a list of ``{'label': ..., 'sales':
..., 'qty': ...}`` rows into shapes on a slide and never looks at where the
numbers came from. That is what lets two dashboards on two completely different
fact sources export decks that are byte-comparable.

WHY IT LIVES HERE and not in sales_mail_main.py, where it grew up: those
methods were part of PbiSalesMailEngineMixin, and "Sales Analysis with
Salesman" (sales_mail_sman_main.py) reached them by instantiating
PbiSalesMailController. When the bidata-backed boards moved out to
pbi_sales_temp_dashboards, that made this module depend on the temp one —
backwards, since the whole point of the temp container is that it can be
dropped without taking anything else with it. Splitting the presentation half
off here inverts it: both decks import from this module, and nothing outside
pbi_sales_temp_dashboards imports from pbi_sales_temp_dashboards.

The mixin is deliberately NOT an http.Controller — see sales_kpi_main.py's
PbiSalesKpiEngineMixin for why subclassing a live controller is a trap.
PbiSalesPptx at the bottom is the plain concrete class for callers that want
the helpers without inheriting them.

The two attributes the mixin expects from its host are ``_series_order``
(defaulted here) and, for _pptx_add_tiles_slide only — which stayed behind in
sales_mail_main.py because it is bidata-specific — ``_source_label``.
"""

# python-pptx is OPTIONAL — see pbi_dashboards/controllers/optional_deps.py.
# Guarded so this module, and therefore the whole addon, still imports on a
# server that does not have it; without the guard a missing package makes the
# module uninstallable rather than merely making one button unavailable.
try:
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
    from pptx.enum.text import MSO_AUTO_SIZE, MSO_ANCHOR, PP_ALIGN
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.oxml import parse_xml
    from pptx.oxml.ns import qn, nsdecls
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
except ImportError:
    CategoryChartData = XL_CHART_TYPE = XL_LEGEND_POSITION = None
    XL_LABEL_POSITION = MSO_AUTO_SIZE = MSO_ANCHOR = PP_ALIGN = None
    MSO_SHAPE = parse_xml = qn = nsdecls = None

    def Inches(value):
        return value

    def Pt(value):
        return value

    def RGBColor(*rgb):
        return None


def _ensure_pptx_loaded():
    global CategoryChartData, XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
    global MSO_AUTO_SIZE, MSO_ANCHOR, PP_ALIGN, MSO_SHAPE, parse_xml, qn, nsdecls
    global Inches, Pt, RGBColor
    global PPTX_COLOR_2024, PPTX_COLOR_2025, PPTX_COLOR_BUDGET, PPTX_PIE_PALETTE
    global PPTX_TILE_COLORS, PPTX_TILE_GOOD, PPTX_TILE_BAD, PPTX_LINE_ACHIEVEMENT, PPTX_LINE_YOY, PPTX_GRIDLINE_COLOR
    if CategoryChartData is not None:
        return True
    try:
        from pptx.chart.data import CategoryChartData as _CCD
        from pptx.enum.chart import XL_CHART_TYPE as _XCT, XL_LEGEND_POSITION as _XLP, XL_LABEL_POSITION as _XLAP
        from pptx.enum.text import MSO_AUTO_SIZE as _MAS, MSO_ANCHOR as _MA, PP_ALIGN as _PPA
        from pptx.enum.shapes import MSO_SHAPE as _MS
        from pptx.oxml import parse_xml as _px
        from pptx.oxml.ns import qn as _qn, nsdecls as _nsd
        from pptx.util import Inches as _Inches, Pt as _Pt
        from pptx.dml.color import RGBColor as _RGBColor
        CategoryChartData, XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION = _CCD, _XCT, _XLP, _XLAP
        MSO_AUTO_SIZE, MSO_ANCHOR, PP_ALIGN, MSO_SHAPE = _MAS, _MA, _PPA, _MS
        parse_xml, qn, nsdecls, Inches, Pt, RGBColor = _px, _qn, _nsd, _Inches, _Pt, _RGBColor
        # Office accents 1-3, sampled from the client's Excel deck — see the
        # module-level copies below for the full note. The two blocks MUST stay
        # identical: this one wins whenever python-pptx is imported lazily.
        PPTX_COLOR_2024 = RGBColor(0xa5, 0xa5, 0xa5)    # grey   - Last Year
        PPTX_COLOR_2025 = RGBColor(0xed, 0x7d, 0x31)    # orange - This Year
        PPTX_COLOR_BUDGET = RGBColor(0x44, 0x72, 0xc4)  # blue   - Target
        PPTX_PIE_PALETTE = [RGBColor(0x2a, 0x78, 0xd6), RGBColor(0x1b, 0xaf, 0x7a), RGBColor(0xed, 0xa1, 0x00),
                            RGBColor(0x4a, 0x3a, 0xa7), RGBColor(0x17, 0xa2, 0xb8), RGBColor(0xe3, 0x49, 0x48),
                            RGBColor(0x8e, 0x44, 0xad), RGBColor(0x16, 0xa0, 0x85), RGBColor(0xd3, 0x54, 0x00),
                            RGBColor(0x2c, 0x3e, 0x50)]
        PPTX_TILE_COLORS = [RGBColor(0xed, 0x7d, 0x31), RGBColor(0x44, 0x72, 0xc4), RGBColor(0xa5, 0xa5, 0xa5)]
        PPTX_TILE_GOOD = RGBColor(0xb8, 0xff, 0xc9)
        PPTX_TILE_BAD = RGBColor(0xff, 0xd2, 0xd2)
        PPTX_LINE_ACHIEVEMENT = RGBColor(0xff, 0xc0, 0x00)  # gold - Vs. Target
        PPTX_LINE_YOY = RGBColor(0x5b, 0x9b, 0xd5)         # sky  - Vs. Last Year
        PPTX_GRIDLINE_COLOR = RGBColor(0xe1, 0xe0, 0xd9)
        return True
    except ImportError:
        return False


from .main import _pptx_fill_marked_text



# Bar colours — sampled from the client's own Excel deck ("SEP-REPORT From
# HHS.pdf"), which is what this export is a rebuild of: Office theme accents
# 1-3, the default a three-series clustered column chart gets in Excel. Kept in
# step with the --report-* block at the top of
# static/src/css/sales_mail_sman_dashboard.css — the board on screen and the
# deck it exports have to be the same colours, and before this they were not
# (the web board drew This Year blue and Last Year aqua; the deck had them the
# other way round).
PPTX_COLOR_2024 = RGBColor(0xa5, 0xa5, 0xa5)    # grey   - Last Year (A. 2024)
PPTX_COLOR_2025 = RGBColor(0xed, 0x7d, 0x31)    # orange - This Year (A. 2025)
PPTX_COLOR_BUDGET = RGBColor(0x44, 0x72, 0xc4)  # blue   - Target
PPTX_PIE_PALETTE = [RGBColor(0x2a, 0x78, 0xd6), RGBColor(0x1b, 0xaf, 0x7a), RGBColor(0xed, 0xa1, 0x00),
                    RGBColor(0x4a, 0x3a, 0xa7), RGBColor(0x17, 0xa2, 0xb8), RGBColor(0xe3, 0x49, 0x48),
                    RGBColor(0x8e, 0x44, 0xad), RGBColor(0x16, 0xa0, 0x85), RGBColor(0xd3, 0x54, 0x00),
                    RGBColor(0x2c, 0x3e, 0x50)]
# Excel/PowerPoint custom number-format codes for the value axis — each
# trailing comma divides the raw value by 1000, matching the web
# dashboard's fmtM ("630.6M")/fmtK ("22.8K") abbreviations instead of
# python-pptx's default "General" (raw unformatted numbers).
PPTX_AXIS_NUMBER_FORMAT = {'M': '#,##0.0,,"M"', 'K': '#,##0.0,"K"'}

# Slide geometry for a "page" slide (13.333 x 7.5in) — mirrors the web
# page's `.chart-row` grid (chart-col: 1fr, .narrative: 340px, out of a
# 1240px-max .wrap) by carving the same ~27% off the right for a visible
# notes column instead of hiding that text in PowerPoint's Notes pane only.
PPTX_MARGIN = 0.4
PPTX_CONTENT_TOP = 0.95
PPTX_CONTENT_H = 6.35
PPTX_GRID_GAP = 0.2
PPTX_NOTES_W = 3.4
PPTX_NOTES_GAP = 0.25
PPTX_CHART_AREA_W = 13.333 - 2 * PPTX_MARGIN - PPTX_NOTES_W - PPTX_NOTES_GAP
PPTX_NOTES_LEFT = PPTX_MARGIN + PPTX_CHART_AREA_W + PPTX_NOTES_GAP
PPTX_FULL_W = 13.333 - 2 * PPTX_MARGIN

# KPI tile colors — matches .tile-color-0/1/2 in sales_mail_dashboard.css
# (--series-1 blue, #16a2a6 teal, --series-3 orange), cycled This Year/
# Target/Last Year per renderKpis()'s `tile-color-${i % 3}` in
# sales_mail_dashboard_new.js. The two "good"/"bad" badge colors are that
# same CSS's `[class*="tile-color-"] .sub .good/.bad` (light tints, since
# the tile background is already a saturated color).
PPTX_TILE_COLORS = [RGBColor(0xed, 0x7d, 0x31), RGBColor(0x44, 0x72, 0xc4), RGBColor(0xa5, 0xa5, 0xa5)]
PPTX_TILE_GOOD = RGBColor(0xb8, 0xff, 0xc9)
PPTX_TILE_BAD = RGBColor(0xff, 0xd2, 0xd2)

# comboBarLineChart's secondary-axis line colors (--report-vs-target gold /
# --report-vs-last-year sky in sales_mail_sman_dashboard.js's lineColors()) —
# Page 2 only. Office accents 4 and 5, the pair the client's deck uses.
PPTX_LINE_ACHIEVEMENT = RGBColor(0xff, 0xc0, 0x00)  # gold - Vs. Target
PPTX_LINE_YOY = RGBColor(0x5b, 0x9b, 0xd5)         # sky  - Vs. Last Year

# Matches the web dashboard's own `.gridline { stroke: var(--grid) }`
# (--grid: #e1e0d9 in sales_dashboard.css) — native pptx charts default to
# a darker gray that competes with data labels sitting right at gridline
# height, so every bar/column chart gets this lighter color explicitly.
PPTX_GRIDLINE_COLOR = RGBColor(0xe1, 0xe0, 0xd9)


class PbiSalesPptxMixin:
    """The slide-building half of a Sales Analysis deck."""

    # PPTX bar order, as (amount_key, qty_key, label, colour) in the order the
    # bars are drawn — kept in one place so the keys, the legend labels and
    # the colours cannot drift apart, and mirroring the on-screen order in
    # static/src/js/sales_mail_dashboard_new.js. "Sales Analysis - New" draws
    # Target first; see PbiSalesMailNewController.
    _series_order = [
        ('budget', 'budgetQty', 'Target', PPTX_COLOR_BUDGET),
        ('sales', 'qty', 'This Year', PPTX_COLOR_2025),
        ('prevYearSales', 'prevYearQty', 'Last Year', PPTX_COLOR_2024),
    ]

    # ------------------------------------------------------------------
    # PPTX export
    # ------------------------------------------------------------------
    def _pptx_style_series(self, chart, colors):
        for i, series in enumerate(chart.plots[0].series):
            if i < len(colors):
                series.format.fill.solid()
                series.format.fill.fore_color.rgb = colors[i]

    def _pptx_style_pie_points(self, chart, colors):
        points = chart.plots[0].series[0].points
        for i, pt in enumerate(points):
            if i < len(colors):
                pt.format.fill.solid()
                pt.format.fill.fore_color.rgb = colors[i]

    def _pptx_kpi_block(self, fmt_fn, this_year, target, last_year, prefix):
        """Mirrors renderKpis()'s `block()` helper in
        sales_mail_dashboard_new.js: This Year/Target/Last Year, each tile
        carrying the same vs-LY/Achv %-badge folded in (This Year -> vs LY,
        Target -> Achv, Last Year -> none)."""
        def sub(value, compared, badge_prefix):
            if not compared:
                return None, None
            p = value / compared * 100
            return f"{badge_prefix} {p:.1f}%", p >= 100
        ly_text, ly_good = sub(this_year, last_year, 'vs LY')
        tgt_text, tgt_good = sub(this_year, target, 'Achv')
        return [
            {'value': fmt_fn(this_year), 'label': f'{prefix} - This Year', 'sub_text': ly_text, 'sub_good': ly_good},
            {'value': fmt_fn(target), 'label': f'{prefix} - Target', 'sub_text': tgt_text, 'sub_good': tgt_good},
            {'value': fmt_fn(last_year), 'label': f'{prefix} - Last Year', 'sub_text': None, 'sub_good': None},
        ]

    def _pptx_add_kpi_tile(self, slide, left, top, width, height, tile, color):
        """One colored tile card — mirrors the web's `.pbi-kpi` (value/
        label/sub-badge stack on a solid-color rounded box)."""
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top),
                                        Inches(width), Inches(height))
        shape.fill.solid()
        shape.fill.fore_color.rgb = color
        shape.line.fill.background()
        shape.shadow.inherit = False
        tf = shape.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.margin_left = tf.margin_right = Pt(4)
        tf.margin_top = tf.margin_bottom = Pt(2)

        p0 = tf.paragraphs[0]
        p0.alignment = PP_ALIGN.CENTER
        r0 = p0.add_run()
        r0.text = tile['value']
        r0.font.bold = True
        r0.font.size = Pt(15)
        r0.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

        p1 = tf.add_paragraph()
        p1.alignment = PP_ALIGN.CENTER
        r1 = p1.add_run()
        r1.text = tile['label']
        r1.font.size = Pt(8.5)
        r1.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

        if tile['sub_text']:
            p2 = tf.add_paragraph()
            p2.alignment = PP_ALIGN.CENTER
            r2 = p2.add_run()
            r2.text = tile['sub_text']
            r2.font.bold = True
            r2.font.size = Pt(8)
            r2.font.color.rgb = PPTX_TILE_GOOD if tile['sub_good'] else PPTX_TILE_BAD

    def _pptx_grid_cells(self, n, stacked=False):
        """(left, top, width, height) in inches for n charts (1, 2, 4 or 8)
        within the chart area of a 13.333x7.5in slide — i.e. everything
        left of the notes sidebar (PPTX_NOTES_LEFT..). 1/2/4 match the web
        page's own .pbi-card-grid.two/.four layout (side-by-side / 2x2). 8
        is used only by the 2-chart-per-toggle-state pages consolidated
        onto one slide (4 states x 2 charts, arranged 4 columns x 2 rows).
        `stacked` mirrors the web's `.pbi-card-grid.two.stacked-full`
        modifier (grid-template-columns: 1fr) — full-width, one chart
        above the other — used by the n==2 pages whose XML carries that
        class (dept-region-trends, main-groups, subgroups-top8,
        lcac-subgroups, projects-productgroups) instead of the plain
        `.two` side-by-side pages (subgroups/maingroups/departments
        distribution donuts)."""
        left0, top0, total_w, total_h, gap = PPTX_MARGIN, PPTX_CONTENT_TOP, PPTX_CHART_AREA_W, PPTX_CONTENT_H, PPTX_GRID_GAP
        if n == 1:
            return [(left0, top0, total_w, total_h)]
        if n == 2:
            if stacked:
                h = (total_h - gap) / 2
                return [(left0, top0, total_w, h), (left0, top0 + h + gap, total_w, h)]
            w = (total_w - gap) / 2
            return [(left0, top0, w, total_h), (left0 + w + gap, top0, w, total_h)]
        if n == 4:
            w, h = (total_w - gap) / 2, (total_h - gap) / 2
            return [
                (left0, top0, w, h), (left0 + w + gap, top0, w, h),
                (left0, top0 + h + gap, w, h), (left0 + w + gap, top0 + h + gap, w, h),
            ]
        if n == 8:
            w, h = (total_w - 3 * gap) / 4, (total_h - gap) / 2
            return [
                (left0 + col * (w + gap), top0 + row * (h + gap), w, h)
                for row in range(2) for col in range(4)
            ]
        raise ValueError(f"unsupported chart count for a grid slide: {n}")

    def _pptx_style_gridlines(self, chart):
        """Lightens the value axis's horizontal gridlines (default pptx gray
        is dark enough to fight with data labels that land right at
        gridline height) to the same light gray the web dashboard's own
        SVG gridlines use — see PPTX_GRIDLINE_COLOR."""
        gridlines = chart.value_axis.major_gridlines
        gridlines.format.line.color.rgb = PPTX_GRIDLINE_COLOR
        gridlines.format.line.width = Pt(0.75)

    def _pptx_add_bar_data_labels(self, chart, value_fmt):
        """Shows each bar/column's value above it, matching the web
        dashboard's `.bar-value` labels (groupedBarChart in
        sales_mail_dashboard_new.js) — native pptx charts render bare by
        default."""
        plot = chart.plots[0]
        plot.has_data_labels = True
        dl = plot.data_labels
        dl.number_format = PPTX_AXIS_NUMBER_FORMAT[value_fmt]
        dl.number_format_is_linked = False
        dl.font.size = Pt(7)
        dl.position = XL_LABEL_POSITION.OUTSIDE_END

    def _pptx_add_pie_data_labels(self, chart):
        """Shows each slice's share %, matching the web dashboard's donut
        leader-line labels (donutChart in sales_mail_dashboard_new.js)."""
        plot = chart.plots[0]
        plot.has_data_labels = True
        dl = plot.data_labels
        dl.show_percentage = True
        dl.show_value = False
        dl.number_format = '0.0%'
        dl.number_format_is_linked = False
        dl.font.size = Pt(8)

    def _pptx_add_combo_lines(self, chart, categories, lines):
        """Overlays achievementPct/yoyPct as a secondary-axis line series on
        top of an existing bar chart — mirrors the web's comboBarLineChart
        (Page 2: Department & Region Performance Trends), which the PPTX
        export previously dropped because python-pptx's high-level API has
        no combo/secondary-axis chart type. There's no way to build one
        through that API, so a `<c:lineChart>` plus its own hidden
        secondary c:catAx + visible right-hand c:valAx are spliced into the
        chart's plotArea as raw OOXML instead — python-pptx's chart.plots
        picks the new LinePlot straight back up afterward since it just
        re-scans the plotArea for known chart-type children, so no other
        code needs to know this series wasn't built the normal way."""
        plot_area = chart._chartSpace.chart.plotArea
        bar_chart_el = plot_area.find(qn('c:barChart'))
        base_idx = len(bar_chart_el.findall(qn('c:ser')))

        # Fixed sentinel axIds — only need to be unique within this one
        # chart's own plotArea, never across charts, so no need to derive
        # them from the bar chart's own (randomly-generated) axIds.
        sec_cat_ax_id, sec_val_ax_id = 500000001, 500000002

        def pt_xml(values):
            pts = "".join(f'<c:pt idx="{i}"><c:v>{v}</c:v></c:pt>' for i, v in enumerate(values) if v is not None)
            return f'<c:ptCount val="{len(values)}"/>{pts}'

        cat_xml = "".join(f'<c:pt idx="{i}"><c:v>{c}</c:v></c:pt>' for i, c in enumerate(categories))

        ser_xml = ""
        for i, line in enumerate(lines):
            idx = base_idx + i
            color_hex = "%02X%02X%02X" % (line['color'][0], line['color'][1], line['color'][2])
            ser_xml += f"""
            <c:ser>
              <c:idx val="{idx}"/>
              <c:order val="{idx}"/>
              <c:tx><c:strRef><c:f>Sheet1!$Z${i + 1}</c:f><c:strCache><c:ptCount val="1"/><c:pt idx="0"><c:v>{line['label']}</c:v></c:pt></c:strCache></c:strRef></c:tx>
              <c:spPr><a:ln w="28575"><a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill></a:ln></c:spPr>
              <c:marker><c:symbol val="circle"/><c:size val="6"/><c:spPr><a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill><a:ln><a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill></a:ln></c:spPr></c:marker>
              <c:cat><c:strRef><c:f>Sheet1!$A$2:$A${len(categories) + 1}</c:f><c:strCache><c:ptCount val="{len(categories)}"/>{cat_xml}</c:strCache></c:strRef></c:cat>
              <c:val><c:numRef><c:f>Sheet1!$Y{i + 1}$2:$Y{i + 1}${len(categories) + 1}</c:f><c:numCache><c:formatCode>0.0&quot;%&quot;</c:formatCode>{pt_xml(line['values'])}</c:numCache></c:numRef></c:val>
              <c:smooth val="0"/>
            </c:ser>
            """

        line_chart_el = parse_xml(f"""<c:lineChart {nsdecls('c', 'a', 'r')}>
            <c:grouping val="standard"/>
            <c:varyColors val="0"/>
            {ser_xml}
            <c:marker val="1"/>
            <c:axId val="{sec_cat_ax_id}"/>
            <c:axId val="{sec_val_ax_id}"/>
          </c:lineChart>""")
        bar_chart_el.addnext(line_chart_el)

        sec_cat_ax_el = parse_xml(f"""<c:catAx {nsdecls('c', 'a', 'r')}>
            <c:axId val="{sec_cat_ax_id}"/>
            <c:scaling><c:orientation val="minMax"/></c:scaling>
            <c:delete val="1"/>
            <c:axPos val="b"/>
            <c:majorTickMark val="none"/>
            <c:minorTickMark val="none"/>
            <c:tickLblPos val="none"/>
            <c:crossAx val="{sec_val_ax_id}"/>
            <c:crosses val="autoZero"/>
            <c:auto val="1"/>
            <c:lblAlgn val="ctr"/>
            <c:lblOffset val="100"/>
            <c:noMultiLvlLbl val="0"/>
          </c:catAx>""")
        sec_val_ax_el = parse_xml(f"""<c:valAx {nsdecls('c', 'a', 'r')}>
            <c:axId val="{sec_val_ax_id}"/>
            <c:scaling><c:orientation val="minMax"/></c:scaling>
            <c:delete val="0"/>
            <c:axPos val="r"/>
            <c:numFmt formatCode="0&quot;%&quot;" sourceLinked="0"/>
            <c:majorTickMark val="out"/>
            <c:minorTickMark val="none"/>
            <c:tickLblPos val="nextTo"/>
            <c:crossAx val="{sec_cat_ax_id}"/>
            <c:crosses val="max"/>
          </c:valAx>""")
        # All chart-type elements (barChart, lineChart) must precede all
        # axis elements in c:plotArea's schema order — appending puts these
        # after the existing primary catAx/valAx, which is exactly right.
        plot_area.append(sec_cat_ax_el)
        plot_area.append(sec_val_ax_el)

    def _pptx_add_notes_sidebar(self, slide, notes, notes_already_marked=False):
        """Visible notes column to the right of the chart grid, mirroring
        the web page's `.chart-row` layout (chart-col + .narrative sidebar,
        grid-template-columns: 1fr 340px). This is the ONLY place notes
        live — PowerPoint's separate Notes pane is left empty on purpose
        (see _pptx_add_multi_chart_slide), so the reader sees the commentary
        beside the chart it belongs to rather than having to open a pane."""
        box = slide.shapes.add_textbox(Inches(PPTX_NOTES_LEFT), Inches(PPTX_CONTENT_TOP),
                                        Inches(PPTX_NOTES_W), Inches(PPTX_CONTENT_H))
        box.text_frame.word_wrap = True
        # A combined toggle-page narrative (4 states concatenated, see
        # _combined_narrative) can run long enough to overflow the fixed
        # sidebar height — shrink the font in PowerPoint rather than let it
        # spill past the slide edge.
        box.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        if notes:
            _pptx_fill_marked_text(box.text_frame, notes, heading_size=Pt(12), body_size=Pt(9),
                                    already_marked=notes_already_marked)

    def _pptx_add_multi_chart_slide(self, prs, layout, title, notes, specs, stacked=False, notes_already_marked=False):
        """One slide per web PAGE (or per toggle state), with that page's
        1/2/4 charts arranged in a grid to the left and its narrative in a
        visible sidebar to the right — mirrors the on-screen `.chart-row`
        layout. `specs` is a list of dicts from _bar_spec/_pie_spec, each
        either {'subtitle','type','categories','series','colors','is_pie'}
        or {'subtitle','empty': True} when that chart's data is empty.
        `stacked` is forwarded to _pptx_grid_cells for the n==2 pages that
        need chart-above-chart instead of side-by-side (see its docstring)."""
        slide = prs.slides.add_slide(layout)
        tb = slide.shapes.add_textbox(Inches(0.4), Inches(0.12), Inches(12.5), Inches(0.55))
        p = tb.text_frame.paragraphs[0]
        p.text = title
        p.font.size = Pt(20)
        p.font.bold = True

        for spec, (left, top, width, height) in zip(specs, self._pptx_grid_cells(len(specs), stacked=stacked)):
            subtitle = spec.get('subtitle')
            chart_top, chart_height = top, height
            if subtitle:
                stb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(0.28))
                sp = stb.text_frame.paragraphs[0]
                sp.text = subtitle
                sp.font.size = Pt(12)
                sp.font.bold = True
                chart_top, chart_height = top + 0.3, height - 0.3
            if spec.get('empty'):
                ntb = slide.shapes.add_textbox(Inches(left), Inches(chart_top), Inches(width), Inches(0.4))
                ntb.text_frame.paragraphs[0].text = "No data"
                ntb.text_frame.paragraphs[0].font.size = Pt(11)
                continue
            chart_data = CategoryChartData()
            chart_data.categories = spec['categories']
            for name, values in spec['series']:
                chart_data.add_series(name, values)
            gframe = slide.shapes.add_chart(spec['type'], Inches(left), Inches(chart_top),
                                             Inches(width), Inches(chart_height), chart_data)
            chart = gframe.chart
            chart.has_legend = True
            chart.legend.position = XL_LEGEND_POSITION.BOTTOM
            chart.legend.include_in_layout = False
            chart.font.size = Pt(8)
            if spec.get('is_pie'):
                self._pptx_style_pie_points(chart, spec['colors'])
                self._pptx_add_pie_data_labels(chart)
            else:
                self._pptx_style_series(chart, spec['colors'])
                # Native pptx defaults to overlap=0 (bars in the same
                # cluster touch edge-to-edge) — the web's groupedBarChart
                # always leaves a small gap between them (its `gap = 6`
                # out of up to `barW = 32`), so pull them apart to match.
                chart.plots[0].overlap = -30
                # Native pptx charts default the value axis to "General"
                # format (raw numbers like 630643140) — match the web
                # dashboard's M/K-abbreviated axis labels instead.
                chart.value_axis.tick_labels.number_format = PPTX_AXIS_NUMBER_FORMAT[spec.get('value_fmt', 'M')]
                chart.value_axis.tick_labels.number_format_is_linked = False
                self._pptx_style_gridlines(chart)
                self._pptx_add_bar_data_labels(chart, spec.get('value_fmt', 'M'))
                if spec.get('lines'):
                    self._pptx_add_combo_lines(chart, spec['categories'], spec['lines'])

        # Notes live ONLY in the visible sidebar textbox — PowerPoint's
        # separate Notes pane (shown at the bottom of the editing window) is
        # intentionally left untouched/empty, so a printed or presented deck
        # carries the commentary rather than hiding it.
        self._pptx_add_notes_sidebar(slide, notes, notes_already_marked=notes_already_marked)
        return slide

    def _qty_sorted(self, rows):
        """Every breakdown list from _fetch_bundle is ordered by This-Year
        SALES descending (shared with the paired Value chart/slide). A Qty
        chart/slide needs its OWN This-Year-Qty-descending order instead —
        sort a copy here so the Value chart's list/order is untouched."""
        return sorted(rows or [], key=lambda r: r.get('qty') or 0, reverse=True)

    def _bar_spec(self, rows, series_defs, subtitle=None):
        if not rows:
            return {'subtitle': subtitle, 'empty': True}
        cats = [r['label'] or '—' for r in rows]
        series = [(label, [r.get(key) or 0 for r in rows]) for key, label in series_defs]
        # series_defs is always value_series (sales/budget/prevYearSales,
        # web's fmtM) or qty_series (qty/budgetQty/prevYearQty, web's
        # fmtK) — detect which from the first series key so every call
        # site gets the matching axis format without threading a new arg.
        value_fmt = 'K' if series_defs[0][0] in ('qty', 'budgetQty', 'prevYearQty') else 'M'
        return {'subtitle': subtitle, 'type': XL_CHART_TYPE.COLUMN_CLUSTERED, 'categories': cats, 'series': series,
                'colors': [c for _a, _q, _l, c in self._series_order], 'is_pie': False, 'value_fmt': value_fmt}

    def _combo_spec(self, rows, series_defs, line_defs, subtitle=None):
        """_bar_spec plus a `lines` key carrying achievementPct/yoyPct as a
        secondary-axis overlay — matches the web's comboBarLineChart, used
        only by Page 2 (Department & Region Performance Trends). Consumed
        by _pptx_add_multi_chart_slide -> _pptx_add_combo_lines.
        `line_defs` is a list of (row_key, label, color) tuples."""
        spec = self._bar_spec(rows, series_defs, subtitle)
        if spec.get('empty'):
            return spec
        spec['lines'] = [
            {'label': label, 'color': color, 'values': [r.get(key) for r in rows]}
            for key, label, color in line_defs
        ]
        return spec

    def _pie_spec(self, rows, value_key, subtitle=None):
        rows = [r for r in (rows or []) if (r.get(value_key) or 0) > 0 and r.get('label') != 'Total']
        if not rows:
            return {'subtitle': subtitle, 'empty': True}
        cats = [r['label'] for r in rows]
        series = [('Share', [r.get(value_key) or 0 for r in rows])]
        pie_type = getattr(XL_CHART_TYPE, 'PIE_3D', XL_CHART_TYPE.PIE) if XL_CHART_TYPE else None
        return {'subtitle': subtitle, 'type': pie_type, 'categories': cats, 'series': series,
                'colors': PPTX_PIE_PALETTE, 'is_pie': True}


class PbiSalesPptx(PbiSalesPptxMixin):
    """Concrete, stateless holder of the helpers above.

    For callers that only want to draw slides and have no engine of their
    own to mix into — one module-level instance is safe, the class keeps no
    state. Subclass it (rather than a controller) to change _series_order.
    """

