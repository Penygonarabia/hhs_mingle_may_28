from datetime import date, timedelta

from odoo import http
from odoo.http import request


def _quarter_start(d):
    q_month = (d.month - 1) // 3 * 3 + 1
    return date(d.year, q_month, 1)


def _prev_quarter_range(d):
    start = _quarter_start(d)
    prev_end = start - timedelta(days=1)
    return _quarter_start(prev_end), prev_end


class PbiLoyaltyDashboardController(http.Controller):
    """Backs "PBI Dashboards > Loyalty Dashboards > Loyalty Analysis" — a
    custom OWL dashboard, same visual family as PbiSalesDashboardController,
    reading directly from the raw legacy ``transaction_header``/
    ``transaction_details`` tables (regulartable_api) joined to res.partner
    for tier/region/city, per the Loyalty Analysis Dashboard spec:
    customers per tier, points issued, points redeemed and newly added
    users, all region-wise with a City (and, for points, Customer)
    drill-down.

    "Points issued" nets Invoice (trnh_type='01') against Credit Note
    (trnh_type='02') the same way hhs_loyalty_res_partner nets
    collected/returned regular points, summing trnd_regularpts +
    trnd_bonuspts — the actual points-earned-per-line columns
    hhs_loyalty_invoice_processor's wizard computes and writes (only for
    doc types 01/02). "Points redeemed" reads trnh_type='98' rows (the ERP
    doc-type legend documented in hhs_loyalty_invoice_processor/models/
    loyalty_points_processed_log.py: 01=Invoice, 02=Credit Note,
    97=Expiry, 98=Redeem, 99=Adjustment), summing trnd_lpoint since
    regularpts/bonuspts are never populated for doc type 98.

    A customer's transaction rows are matched via
    res.partner.ref = transaction_header.trnh_cstno, the same join
    hhs_loyalty_invoice_processor/models/loyalty_invoice_processor.py uses.
    """

    # ------------------------------------------------------------------
    # low-level helpers
    # ------------------------------------------------------------------
    def _query(self, sql, params=()):
        request.env.cr.execute(sql, params)
        cols = [d[0] for d in request.env.cr.description]
        return [dict(zip(cols, row)) for row in request.env.cr.fetchall()]

    def _has_access(self):
        user = request.env.user
        menu = request.env.ref("pbi_dashboards.menu_pbi_loyalty_analysis", raise_if_not_found=False)
        if not menu:
            return False
        allowed = request.env["dashboard.rights.menu"].sudo().allowed_menu_ids(user)
        return menu.id in allowed

    def _period_range(self, period, date_from=None, date_to=None):
        """Returns (start, end) dates for a Period filter value. "This X" is
        to-date (start of X through today); "Last X" is the complete prior
        period — standard BI-dashboard convention, no other precedent exists
        in this app for these preset labels."""
        today = date.today()
        if period == "custom":
            def _parse(v, default):
                try:
                    return date.fromisoformat(v) if v else default
                except (TypeError, ValueError):
                    return default
            start = _parse(date_from, today)
            end = _parse(date_to, today)
            return (start, end) if start <= end else (end, start)
        if period == "this_week":
            return today - timedelta(days=today.weekday()), today
        if period == "this_month":
            return today.replace(day=1), today
        if period == "this_quarter":
            return _quarter_start(today), today
        if period == "this_year":
            return today.replace(month=1, day=1), today
        if period == "last_week":
            this_week_start = today - timedelta(days=today.weekday())
            return this_week_start - timedelta(days=7), this_week_start - timedelta(days=1)
        if period == "last_month":
            end = today.replace(day=1) - timedelta(days=1)
            return end.replace(day=1), end
        if period == "last_quarter":
            return _prev_quarter_range(today)
        if period == "last_year":
            return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
        return today.replace(month=1, day=1), today  # fallback: this_year

    # ------------------------------------------------------------------
    # "Number of customers per tier" — Region -> City (leaf: redirect to
    # the customer list for that city)
    # ------------------------------------------------------------------
    def _tiers(self):
        rows = self._query("SELECT name FROM customer_tier ORDER BY sort_order, name")
        return [r["name"] for r in rows]

    def _tier_rows(self, level, date_from, date_to, drill_region_id=None, region_name=None):
        dim_col, dim_id = {"region": ("wg.name", "wg.id"), "city": ("wcl.name", "wcl.id")}[level]
        clauses = [
            "p.activate_loyalty_feature = true",
            "p.tier_name IS NOT NULL",
            "p.activation_date BETWEEN %s AND %s",
            f"{dim_col} IS NOT NULL",
        ]
        params = [date_from, date_to]
        if region_name and region_name != "all":
            clauses.append("wg.name = %s")
            params.append(region_name)
        if level == "city" and drill_region_id:
            clauses.append("p.work_center_group_id = %s")
            params.append(drill_region_id)
        where = " AND ".join(clauses)
        rows = self._query(f"""
            SELECT {dim_col} AS label, {dim_id} AS id, p.tier_name AS tier, count(*) AS cnt
            FROM res_partner p
            LEFT JOIN work_center_group wg ON wg.id = p.work_center_group_id
            LEFT JOIN work_center_location wcl ON wcl.id = p.work_center_id
            WHERE {where}
            GROUP BY 1, 2, 3
        """, params)

        tiers = self._tiers()
        buckets, order = {}, []
        for r in rows:
            key = (r["label"], r["id"])
            if key not in buckets:
                buckets[key] = {"label": r["label"], "id": r["id"]}
                order.append(key)
            buckets[key][r["tier"]] = buckets[key].get(r["tier"], 0) + int(r["cnt"])
        result = []
        for key in order:
            row = buckets[key]
            for t in tiers:
                row.setdefault(t, 0)
            result.append(row)
        result.sort(key=lambda r: sum(r.get(t, 0) for t in tiers), reverse=True)
        return result, tiers

    # ------------------------------------------------------------------
    # "Points issued" / "Points redeemed" — Region -> City -> Customer
    # (leaf: redirect to that customer's loyalty points history)
    #
    # "Points issued" (doc types 01/02) sums trnd_regularpts + trnd_bonuspts —
    # the actual points-earned-on-this-line columns hhs_loyalty_invoice_
    # processor computes and writes per invoice/credit-note line, netting
    # Credit Note against Invoice the same way hhs_loyalty_res_partner nets
    # collected/returned points. "Points redeemed" (doc type 98) has no
    # such column — that wizard only ever populates regularpts/bonuspts for
    # doc types 01/02 — so it falls back to trnd_lpoint, the only points
    # figure present on every doc type regardless of processing.
    # ------------------------------------------------------------------
    def _points_rows(self, doc_types, level, date_from, date_to, drill_region_id=None, drill_city_id=None,
                      region_name=None):
        dim_col, dim_id = {
            "region": ("wg.name", "wg.id"),
            "city": ("wcl.name", "wcl.id"),
            "customer": ("p.name", "p.id"),
        }[level]
        is_issued = "02" in doc_types
        sign_expr = "CASE WHEN th.trnh_type = '02' THEN -1 ELSE 1 END" if is_issued else "1"
        value_expr = ("(coalesce(td.trnd_regularpts, 0) + coalesce(td.trnd_bonuspts, 0))" if is_issued
                      else "td.trnd_lpoint")
        clauses = [
            "p.activate_loyalty_feature = true",
            "th.trnh_type IN %s",
            "th.trnh_date BETWEEN %s AND %s",
            f"{dim_col} IS NOT NULL",
        ]
        params = [tuple(doc_types), date_from.strftime("%Y%m%d"), date_to.strftime("%Y%m%d")]
        if region_name and region_name != "all":
            clauses.append("wg.name = %s")
            params.append(region_name)
        if level in ("city", "customer") and drill_region_id:
            clauses.append("p.work_center_group_id = %s")
            params.append(drill_region_id)
        if level == "customer" and drill_city_id:
            clauses.append("p.work_center_id = %s")
            params.append(drill_city_id)
        where = " AND ".join(clauses)
        rows = self._query(f"""
            SELECT {dim_col} AS label, {dim_id} AS id,
                   sum({value_expr} * {sign_expr}) AS value
            FROM transaction_header th
            JOIN transaction_details td
                ON td.trnd_no = th.trnh_no AND td.trnd_whouse = th.trnh_whouse
            JOIN res_partner p ON p.ref = th.trnh_cstno
            LEFT JOIN work_center_group wg ON wg.id = p.work_center_group_id
            LEFT JOIN work_center_location wcl ON wcl.id = p.work_center_id
            WHERE {where}
            GROUP BY 1, 2
            ORDER BY 3 DESC
            LIMIT 15
        """, params)
        return [{"label": r["label"], "id": r["id"], "value": float(r["value"] or 0)} for r in rows]

    # ------------------------------------------------------------------
    # "Newly added users" — Region -> City (leaf: redirect to the customer
    # list for that city)
    # ------------------------------------------------------------------
    def _newusers_rows(self, level, date_from, date_to, drill_region_id=None, region_name=None):
        dim_col, dim_id = {"region": ("wg.name", "wg.id"), "city": ("wcl.name", "wcl.id")}[level]
        clauses = [
            "p.activate_loyalty_feature = true",
            "p.activation_date BETWEEN %s AND %s",
            f"{dim_col} IS NOT NULL",
        ]
        params = [date_from, date_to]
        if region_name and region_name != "all":
            clauses.append("wg.name = %s")
            params.append(region_name)
        if level == "city" and drill_region_id:
            clauses.append("p.work_center_group_id = %s")
            params.append(drill_region_id)
        where = " AND ".join(clauses)
        rows = self._query(f"""
            SELECT {dim_col} AS label, {dim_id} AS id, count(*) AS value
            FROM res_partner p
            LEFT JOIN work_center_group wg ON wg.id = p.work_center_group_id
            LEFT JOIN work_center_location wcl ON wcl.id = p.work_center_id
            WHERE {where}
            GROUP BY 1, 2
            ORDER BY 3 DESC
        """, params)
        return [{"label": r["label"], "id": r["id"], "value": int(r["value"] or 0)} for r in rows]

    # ------------------------------------------------------------------
    # "Promotion participation" / "Salesman wise Promotion participation" —
    # flat pivot tables, no drill-down. One row per promotion reference
    # actually used in transaction_details (trnd_promoref), optionally
    # broken down further by the salesman on the header (trnh_salesmanname).
    # "No of Loyalty customers" is the same total on every row — the
    # denominator for the participation-rate comparison — while
    # "No of utilised customers" is the distinct loyalty customers who
    # transacted under that promotion/salesman: doc types 01 (Invoice) and
    # 02 (Credit Note) — the same pair "Points issued" nets, since a
    # credit-note return is still a customer who participated in the
    # promotion, not a non-participant.
    # ------------------------------------------------------------------
    def _total_loyalty_customers(self, region_name=None):
        clauses = ["p.activate_loyalty_feature = true"]
        params = []
        if region_name and region_name != "all":
            clauses.append("wg.name = %s")
            params.append(region_name)
        where = " AND ".join(clauses)
        rows = self._query(f"""
            SELECT count(*) AS cnt
            FROM res_partner p
            LEFT JOIN work_center_group wg ON wg.id = p.work_center_group_id
            WHERE {where}
        """, params)
        return int(rows[0]["cnt"] or 0)

    def _promotion_participation_rows(self, date_from, date_to, region_name=None, by_salesman=False):
        clauses = [
            "th.trnh_type IN ('01', '02')",
            "td.trnd_promoref IS NOT NULL",
            "td.trnd_promoref <> ''",
            "p.activate_loyalty_feature = true",
            "th.trnh_date BETWEEN %s AND %s",
        ]
        params = [date_from.strftime("%Y%m%d"), date_to.strftime("%Y%m%d")]
        if region_name and region_name != "all":
            clauses.append("wg.name = %s")
            params.append(region_name)
        where = " AND ".join(clauses)
        salesman_select = ", coalesce(nullif(th.trnh_salesmanname, ''), 'Unassigned') AS salesman" if by_salesman else ""
        group_by = "1, 2" if by_salesman else "1"
        rows = self._query(f"""
            SELECT td.trnd_promoref AS promo_ref{salesman_select},
                   count(DISTINCT p.id) AS used_customers,
                   min(to_date(th.trnh_date, 'YYYYMMDD')) AS first_date
            FROM transaction_header th
            JOIN transaction_details td
                ON td.trnd_no = th.trnh_no AND td.trnd_whouse = th.trnh_whouse
            JOIN res_partner p ON p.ref = th.trnh_cstno
            LEFT JOIN work_center_group wg ON wg.id = p.work_center_group_id
            WHERE {where}
            GROUP BY {group_by}
            ORDER BY {group_by}
        """, params)

        refs = sorted({r["promo_ref"] for r in rows})
        promos = {}
        if refs:
            promo_rows = self._query("""
                SELECT promotion_reference, promotion_name, promotion_start_date
                FROM lp_setup_promotions
                WHERE promotion_reference IN %s
            """, (tuple(refs),))
            promos = {p["promotion_reference"]: p for p in promo_rows}

        total = self._total_loyalty_customers(region_name)
        result = []
        for r in rows:
            promo = promos.get(r["promo_ref"])
            promo_date = (promo and promo["promotion_start_date"]) or r["first_date"]
            entry = {
                "promoRef": r["promo_ref"],
                "promoName": (promo and promo["promotion_name"]) or r["promo_ref"],
                "date": promo_date.isoformat() if promo_date else None,
                "loyaltyCustomers": total,
                "usedCustomers": int(r["used_customers"] or 0),
            }
            if by_salesman:
                entry["salesman"] = r["salesman"]
            result.append(entry)
        return result

    # ------------------------------------------------------------------
    # routes
    # ------------------------------------------------------------------
    def _fetch_bundle(self, date_from, date_to, region_name=None):
        tier_rows, tiers = self._tier_rows("region", date_from, date_to, region_name=region_name)
        return {
            "tier": {"tiers": tiers, "data": tier_rows},
            "pointsIssued": self._points_rows(("01", "02"), "region", date_from, date_to, region_name=region_name),
            "pointsRedeemed": self._points_rows(("98",), "region", date_from, date_to, region_name=region_name),
            "newUsers": self._newusers_rows("region", date_from, date_to, region_name=region_name),
            "promoParticipation": self._promotion_participation_rows(date_from, date_to, region_name=region_name),
            "promoParticipationSalesman": self._promotion_participation_rows(
                date_from, date_to, region_name=region_name, by_salesman=True),
        }

    @http.route('/pbi_dashboards/loyalty/data', type='json', auth='user')
    def loyalty_dashboard_data(self, period='this_year', dateFrom=None, dateTo=None, region='all'):
        if not self._has_access():
            return {'error': 'You do not have access to this dashboard.'}
        try:
            date_from, date_to = self._period_range(period, dateFrom, dateTo)
            data = self._fetch_bundle(date_from, date_to, region)
            data['dateFrom'] = date_from.isoformat()
            data['dateTo'] = date_to.isoformat()
            return data
        except Exception as e:
            return {'error': str(e)}

    @http.route('/pbi_dashboards/loyalty/drill', type='json', auth='user')
    def loyalty_dashboard_drill(self, chart='tier', level='city', period='this_year',
                                 dateFrom=None, dateTo=None, drillRegionId=None, drillCityId=None, region='all'):
        if not self._has_access():
            return {'error': 'You do not have access to this dashboard.'}
        try:
            date_from, date_to = self._period_range(period, dateFrom, dateTo)
            if chart == 'tier':
                data, tiers = self._tier_rows(level, date_from, date_to, drillRegionId, region)
                return {'data': data, 'tiers': tiers}
            if chart == 'newUsers':
                return {'data': self._newusers_rows(level, date_from, date_to, drillRegionId, region)}
            if chart == 'pointsIssued':
                return {'data': self._points_rows(('01', '02'), level, date_from, date_to, drillRegionId, drillCityId, region)}
            if chart == 'pointsRedeemed':
                return {'data': self._points_rows(('98',), level, date_from, date_to, drillRegionId, drillCityId, region)}
            return {'error': f'Unknown chart: {chart}'}
        except Exception as e:
            return {'error': str(e)}
