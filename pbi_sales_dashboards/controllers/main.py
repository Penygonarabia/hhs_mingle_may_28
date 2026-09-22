"""Shared presentation helpers for the sales dashboards' PowerPoint export
and their on-screen narrative text — number formatting and the
**bold**/##heading## marked-text convention.

The deck goes ONE WAY. This file used to also carry the read-back half — a
slide-title-to-note-section map, a slide-title reader and a run-formatting
parser that reconstructed the marked form from a deck's notes textbox — so a
note edited in PowerPoint could be imported again. Nothing reads a deck any
more (see sales_mail_sman_main's docstring), and all three went with the last
importer.

No controller lives here any more. This file used to also hold
PbiSalesDashboardController, serving the original "Sales Dashboard" OWL board
on /pbi_dashboards/sales/{data,region_drill,export.pptx,import_notes}. That
board was retired when 533087ef deleted its menu (menu_pbi_sales_dashboard_app)
and its ir.actions.client record, and reused the name "Sales Dashboard" for the
KPI board — but the routes, the 1,181-line sales_dashboard.js and an access
check on the by-then-deleted menu xmlid were all left behind. Since no action
carried its client tag, nothing could open it: the routes answered every caller
"You do not have access to this dashboard", and the asset shipped in every
user's backend bundle. Removed 2026-08-29.

What remains is imported by the boards that ARE live — sales_pptx.py and
sales_mail_sman_main.py here — so treat this as a library, not a place to add
routes.
"""


import re


# python-pptx is OPTIONAL — see pbi_dashboards/controllers/optional_deps.py.
# Guarded so this module, and therefore the whole addon, still imports on a
# server that does not have it; without the guard a missing package makes the
# module uninstallable rather than merely making one button unavailable.
try:
    from pptx.util import Pt
    from pptx.dml.color import RGBColor
except ImportError:  # server without python-pptx
    # Stand-ins, needed only so the module-level constants below still
    # evaluate. Nothing reaches them: every path that draws a slide goes
    # through a route that refuses first (optional_deps.PPTX_AVAILABLE).
    def Pt(value):
        return value

    def RGBColor(*rgb):
        return None

MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]

# The "Year" filter also accepts a single "YYYY-MM" month value (e.g. "2025-03").
MONTH_VALUE_RE = re.compile(r"^(\d{4})-(\d{2})$")

PPTX_COLOR_2024 = RGBColor(0x2a, 0x78, 0xd6)
PPTX_COLOR_2025 = RGBColor(0x1b, 0xaf, 0x7a)
PPTX_COLOR_BUDGET = RGBColor(0xed, 0xa1, 0x00)

# Mirrors the JS-side NOTE_HEADING_RE / highlightFigures in sales_dashboard.js
# so a slide's speaker notes are bold-formatted the same way the on-screen
# narrative is: the YTD line as a heading, figures (M/K amounts, comma-grouped
# numbers, percentages) in bold within ordinary sentences.
PPTX_NOTES_HEADING_RE = re.compile(r'^Year-to-date .+ performance$', re.IGNORECASE)
PPTX_NOTES_FIGURE_RE = re.compile(r'[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|[+-]?\d+(?:\.\d+)?[MK]\b|[+-]?\d+(?:\.\d+)?%')
PPTX_NOTES_BOLD_RUN_RE = re.compile(r'\*\*(.+?)\*\*')


def _pptx_marked_text(plain_text):
    """Turns a freshly-generated plain-text narrative into the canonical
    **bold**/##heading## marked form — the same bold spans _pptx_write_notes
    turns into real runs, and the form the dashboards display and diff a
    typed note against to tell an override from an untouched narrative."""
    lines = []
    for line in plain_text.split('\n'):
        if PPTX_NOTES_HEADING_RE.match(line):
            lines.append(f"##{line}##")
            continue
        pos = 0
        out = []
        for m in PPTX_NOTES_FIGURE_RE.finditer(line):
            if m.start() > pos:
                out.append(line[pos:m.start()])
            out.append(f"**{m.group(0)}**")
            pos = m.end()
        out.append(line[pos:])
        lines.append(''.join(out))
    return '\n'.join(lines)


def _pptx_fill_marked_text(text_frame, plain_text, heading_size=Pt(14), body_size=None, already_marked=False):
    """Shared renderer for a **bold**/##heading## marked narrative into any
    pptx text frame — PowerPoint's hidden Notes pane (_pptx_write_notes) or
    a visible on-slide textbox (the sales-mail dashboards' notes sidebar,
    mirroring the web page's `.narrative` column) both go through this.
    `already_marked=True` skips the auto-figure-marking pass for text that
    is already in canonical **bold**/##heading## form — a note stored in
    pbi.dashboard.note, which carries its own (possibly non-figure,
    user-added) bold spans. Re-running _pptx_marked_text on that would scan
    for numeric figures inside text that already has literal '**' in it,
    doubling up the markers and corrupting every bold span from the first
    stray match onward."""
    text_frame.clear()
    marked = plain_text if already_marked else _pptx_marked_text(plain_text)
    for i, line in enumerate(marked.split('\n')):
        p = text_frame.paragraphs[0] if i == 0 else text_frame.add_paragraph()
        p.space_after = Pt(10)
        heading_m = re.fullmatch(r'##(.*)##', line)
        if heading_m:
            run = p.add_run()
            run.text = heading_m.group(1)
            run.font.bold = True
            run.font.size = heading_size
            continue
        pos = 0
        for m in PPTX_NOTES_BOLD_RUN_RE.finditer(line):
            if m.start() > pos:
                r = p.add_run()
                r.text = line[pos:m.start()]
                if body_size:
                    r.font.size = body_size
            run = p.add_run()
            run.text = m.group(1)
            run.font.bold = True
            if body_size:
                run.font.size = body_size
            pos = m.end()
        if pos < len(line):
            r = p.add_run()
            r.text = line[pos:]
            if body_size:
                r.font.size = body_size


def _pfmt_m(n):
    return f"{(n or 0) / 1e6:.1f}M"


def _pfmt(n):
    return f"{int(round(n or 0)):,}"


def _pshare(part, total):
    return f"{round((part or 0) / total * 100)}%" if total else "–"
