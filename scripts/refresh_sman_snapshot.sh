#!/usr/bin/env bash
# Rebuild v_pbi_sales_sman_fact and show what moved.
#
#   ./scripts/refresh_sman_snapshot.sh                    # dbprod defaults
#   DB=hhs_v3 WEB=web-1 DBC=db-1 ./scripts/refresh_sman_snapshot.sh
#   ./scripts/refresh_sman_snapshot.sh 2026 6             # report one month
#
# WHY YOU NEED THIS. The "… with Salesman" boards do not read transaction_details.
# They read v_pbi_sales_sman_fact, which is a MATERIALIZED VIEW -- a snapshot. Edit
# or delete an invoice line and the tile does not move, because the snapshot still
# holds the old rows. Only a rebuild changes what the board shows.
#
# AND WHY IT DOES NOT REBUILD ITSELF. Postgres statement triggers auto-queue a
# refresh, but only on MASTER-DATA tables -- product_category, res_region,
# sub_category, sale_types and friends. transaction_details deliberately has NO
# trigger: a rebuild costs ~16s of database CPU and that table is far too hot to
# fire on. So a master-data fix (creating the ATOM category, say) reaches the
# chart on its own in a minute or two, while a transaction-row edit (deleting a
# credit note) does not, and waits for the nightly 02:30 cron unless you run this.
#
# Restarting Odoo does NOT help. This is a database object, not the asset cache.
#
# Refreshing through the model rather than raw SQL, because that is what the cron
# calls -- it keeps whatever bookkeeping the model does consistent.
set -euo pipefail

DB="${DB:-dbprod}"
WEB="${WEB:-cloud-web-1}"
DBC="${DBC:-cloud-db-1}"
YR="${1:-}"
MTH="${2:-}"

if [ -n "$YR" ] && [ -n "$MTH" ]; then
    FILTER="AND yr = $YR AND mth = $MTH"
    LABEL="$YR-$(printf '%02d' "$MTH")"
else
    FILTER="AND yr >= 2026"
    LABEL="2026 onwards"
fi

for c in "$WEB" "$DBC"; do
    docker exec "$c" true 2>/dev/null || {
        echo "container '$c' is not running. Set WEB= and DBC= if they are named differently here." >&2
        exit 1; }
done

snapshot () {
    docker exec "$DBC" psql -U odoo -d "$DB" -qtA -F'|' -c "
        SELECT yr, mth, SUM(qty)::numeric, ROUND(SUM(amount)::numeric,2)
        FROM v_pbi_sales_sman_fact WHERE in_scope $FILTER
        GROUP BY 1,2 ORDER BY 1,2;"
}

echo "== $LABEL, snapshot BEFORE =="
snapshot

echo
echo "== rebuilding (~16s of database CPU) =="
docker exec -i "$WEB" odoo shell -c /etc/odoo/odoo.conf \
    --db_host=db --db_user=odoo --db_password=odoo -d "$DB" \
    --no-http --log-level=error --logfile=/tmp/refresh_sman.log <<'PY' 2>&1 | grep -vE '^\s*$' || true
env['pbi.sales.sman.fact'].refresh_fact()
env.cr.commit()
print('refresh_fact() committed')
PY

echo
echo "== $LABEL, snapshot AFTER =="
snapshot

echo
echo "If nothing moved, check in this order:"
echo "  1. Did the underlying change commit?"
echo "       SELECT count(*) FROM transaction_header WHERE TRIM(trnh_no)='<doc>';"
echo "  2. Which board are you looking at? The \"New\" boards read v_bidata_live,"
echo "     NOT this snapshot -- no refresh will ever change them."
echo "  3. Is cron 92 active? Deactivating it also silently disables the"
echo "     master-data triggers, not just the nightly run."
