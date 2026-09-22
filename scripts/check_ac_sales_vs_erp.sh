#!/usr/bin/env bash
# Re-run the AC monthly measure against dbprod and tally it against the ERP's
# own report, whose figures are frozen in EXPECTED below (as supplied 2026-09-03).
#
#   ./scripts/check_ac_sales_vs_erp.sh            # all 19 months
#   ./scripts/check_ac_sales_vs_erp.sh 2026-01 2026-07   # only these
#
# Reads ac_sales_by_month_cumulative.sql next to it, so the measure can never
# drift from the committed definition. Read-only; nothing is written to dbprod.
#
# Why this exists: the legacy feed posts pending documents IN PLACE (status
# N -> P) without touching write_date, so timestamps are useless as a freshness
# signal -- on 2026-09-03 all 117 'N' documents flipped mid-session and moved
# May/June/July. Re-running is the only way to see where the tally stands.
#
# KNOWN VARIANCES as of 2026-09-03 -- every one is understood; do not
# re-investigate these without new information:
#
#   QUANTITY, four months, ERP-side casing. 2025-10 +10, 2025-11 +7, 2025-12 +2,
#   2026-02 +51. Six lines carry a part number typed in lower case
#   (MSTS24CRN2AG15-f, MTBTVE48HWN1-NP-f, MFTGAV50CRN1-NP-f,
#   MSTS12CRNAG15-NP-f, MSTS12CRNAG15-f) against the -F rows the catalog holds.
#   This measure upper-cases both sides of every part-number join, matches them
#   and counts their units; the ERP's report matches case-sensitively and drops
#   them. All six are tagged, in catalog and in scope -- they are real machines,
#   and THIS SIDE IS THE CORRECT ONE. Value agrees to the cent in all four
#   months because value is ungated, which is what makes the signature
#   diagnostic. Fixing it means normalising the casing in the ERP; do NOT
#   "fix" it here, that would mean dropping 70 units we correctly count.
#
#   QUANTITY, 2026-01 +224. Accepted deliberately -- see
#   dbprod_ac_scope_data_fixes.sql. The ERP counts that line's money but not its
#   machines.
#
#   VALUE, all 19 months now agree. 2026-06's SAR 1,194.05 was traced to
#   CR20112352, a POSTED credit note for goods a customer returned that the
#   bidata feed never received (zero rows there; bi_lastmodifieddate stops at
#   2026-04-15). The document was DELETED from this database on 2026-09-03 at the
#   user's direction so the month would match bidata -- see
#   delete_CR20112352_bidata_align.sql, which holds the full reasoning, the
#   backup tables and the restore statements. It was not a defect: the figures
#   before the deletion were the accurate ones, and June no longer reflects that
#   return.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL="$DIR/ac_sales_by_month_cumulative.sql"
CONTAINER="${CONTAINER:-cloud-db-1}"
DB="${DB:-dbprod}"

[ -f "$SQL" ] || { echo "missing $SQL" >&2; exit 1; }
docker exec "$CONTAINER" true 2>/dev/null || {
  echo "container '$CONTAINER' not running (colima start && docker start $CONTAINER)" >&2; exit 1; }

TMP="$(mktemp -t ac_sales_check.XXXXXX)"
trap 'rm -f "$TMP"' EXIT
docker exec -i "$CONTAINER" psql -U odoo -d "$DB" -q -v ON_ERROR_STOP=1 --csv -f - < "$SQL" > "$TMP"

# The heredoc below is python's stdin, so the CSV is passed as a FILE, not piped.
python3 - "$TMP" "$@" <<'PY'
import csv, sys
from decimal import Decimal

# The ERP report's figures, as supplied 2026-09-03. Update only alongside a new report.
EXPECTED = {
 (2025,1):("22144","46939997.77"), (2025,2):("22863","47412225.69"),
 (2025,3):("21613","46870780.10"), (2025,4):("29268","65104480.07"),
 (2025,5):("32567","78199419.99"), (2025,6):("25711","55680259.44"),
 (2025,7):("26863","56355763.29"), (2025,8):("27265","59211533.49"),
 (2025,9):("26415","57784324.23"), (2025,10):("15803","36001584.87"),
 (2025,11):("11838","27204053.72"), (2025,12):("9200","24240381.45"),
 (2026,1):("22263","50158442.23"), (2026,2):("26858","53296708.87"),
 (2026,3):("24512","50042110.82"), (2026,4):("18685","40723340.76"),
 (2026,5):("21175","44285156.24"), (2026,6):("27300","62370711.67"),
 (2026,7):("18202","44492262.14"),
}
csv_path = sys.argv[1]
want = set()
for a in sys.argv[2:]:
    y, m = a.split('-'); want.add((int(y), int(m)))

actual = {(int(r['yr']), int(r['mth'])): (Decimal(r['sales_qty']), Decimal(r['sales_value']))
          for r in csv.DictReader(open(csv_path))}

keys = sorted(k for k in EXPECTED if not want or k in want)
hdr = f"{'period':8} | {'exp qty':>9} {'db qty':>9} {'Δ':>8} | {'exp value':>15} {'db value':>15} {'Δ':>13}"
print(hdr); print('-' * len(hdr))
tq = tv = 0; okq = okv = 0
for k in keys:
    eq, ev = Decimal(EXPECTED[k][0]), Decimal(EXPECTED[k][1])
    if k not in actual:
        print(f"{k[0]}-{k[1]:02d}  | {eq:>9,} {'--':>9} {'--':>8} | {ev:>15,} {'--':>15} {'--':>13}")
        continue
    aq, av = actual[k]; dq = aq - eq; dv = av - ev
    tq += dq; tv += dv; okq += dq == 0; okv += dv == 0
    print(f"{k[0]}-{k[1]:02d}  | {eq:>9,} {aq:>9,} {dq:>+8,} | {ev:>15,} {av:>15,} {dv:>+13,}"
          + ("" if (dq == 0 and dv == 0) else "  <-"))
print('-' * len(hdr))
print(f"{'TOTAL':8} | {'':>9} {'':>9} {tq:>+8,} | {'':>15} {'':>15} {tv:>+13,}")
print(f"\ntally: {okq}/{len(keys)} months on qty, {okv}/{len(keys)} on value")
print("known: qty gaps in 2025-10/11/12 and 2026-02 are ERP-side lower-case part")
print("       numbers -- this side counts them correctly, see the header.")
print("       2026-01 +224 accepted. 2026-06 matches only because CR20112352 was")
print("       deleted -- a real credit note bidata never had; see the header.")
PY
