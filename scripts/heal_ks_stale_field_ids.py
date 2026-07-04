"""Heal stale ir.model.fields ids stored on KS Dashboard Ninja items.

KS stores each item's measure / list-column selections both as a real
many2many onto ``ir.model.fields`` *and*, redundantly, as raw field ids
embedded in the ``ks_many2many_field_ordering`` JSON blob. KS's custom
``ks_read`` rebuilds those four many2many fields **from the blob** whenever it
is present, so the blob is the real source of truth.

When a *source* module is reinstalled, ``ir.model.fields`` is renumbered and
those stored ids go stale. Opening a board that references a now-deleted id
then raises ``MissingError: ir.model.fields(<id>,)``.

This script re-resolves every item's four field lists **by name** against the
current DB, repairing both the blob and the underlying relation table. It is
idempotent: healthy items are left untouched.

Run against a live database with:

    odoo shell -c /etc/odoo/odoo.conf -d <DBNAME> \
        --db_host=db --db_port=5432 --db_user=odoo --db_password=odoo \
        --no-http < scripts/heal_ks_stale_field_ids.py

`env` is provided by the odoo shell. The script commits on success.
"""

import json

_MEASURE_FIELD_KEYS = [
    ("ks_chart_measure_field",     "ks_chart_measure_field_name"),
    ("ks_chart_measure_field_2",   "ks_chart_measure_field_2_name"),
    ("ks_list_view_fields",        "ks_list_view_fields_name"),
    ("ks_list_view_group_fields",  "ks_list_view_group_fields_name"),
]


def heal_item(env, item):
    model = item.ks_model_id.model
    if not model:
        return False
    try:
        ordering = json.loads(item.ks_many2many_field_ordering or "{}")
    except ValueError:
        return False

    Field = env["ir.model.fields"].sudo()
    changed = False
    for id_key, name_key in _MEASURE_FIELD_KEYS:
        names = ordering.get(name_key) or []
        if not names:
            continue
        resolved = []
        for name in names:
            fld = Field.search(
                [("model", "=", model), ("name", "=", name)], limit=1
            )
            if fld:
                resolved.append(fld.id)
        if resolved == (ordering.get(id_key) or []):
            continue
        ordering[id_key] = resolved
        changed = True

        m2m = item._fields[id_key]
        env.cr.execute(
            'DELETE FROM "%s" WHERE "%s" = %%s' % (m2m.relation, m2m.column1),
            (item.id,),
        )
        if resolved:
            env.cr.execute(
                'INSERT INTO "%s" ("%s", "%s") SELECT %%s, unnest(%%s)'
                % (m2m.relation, m2m.column1, m2m.column2),
                (item.id, resolved),
            )

    if changed:
        item.ks_many2many_field_ordering = json.dumps(ordering)
        item.invalidate_recordset()
    return changed


def main(env):
    items = env["ks_dashboard_ninja.item"].with_context(active_test=False).search([])
    healed = 0
    for item in items:
        try:
            if heal_item(env, item):
                healed += 1
                board = item.ks_dashboard_ninja_board_id
                print("healed item %s on board '%s'" % (
                    item.id, board.ks_dashboard_menu_name or board.id))
        except Exception as exc:  # noqa: BLE001 - report and continue
            print("SKIP item %s: %s" % (item.id, exc))
    env.cr.commit()
    print("DONE: healed %s of %s items." % (healed, len(items)))


main(env)  # noqa: F821 - `env` injected by odoo shell
