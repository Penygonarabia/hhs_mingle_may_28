"""dashboard_rights / hooks.

Editing a static CSS/JS asset does NOT, on its own, invalidate the compiled
``web.assets_*`` bundle cached in ``ir_attachment``. A plain container restart
or ``-u`` reloads Python and XML but leaves that bundle in place, so styling
changes to the Users-Setup matrix — notably the Has-Access column-width lock —
kept not showing up on deployed servers even after the file was updated.

Column widths in an Odoo list are computed by the JS/CSS renderer, so that fix
*cannot* be expressed in Python/XML. What we CAN do is make the asset deploy
reliably: drop the cached bundle whenever this module is installed or upgraded,
so the next page load recompiles the CSS/JS from the current source on disk.

Wired from both entry points, because they cover different cases:
  * ``post_init_hook``  -> runs on install (``-i``);
  * ``migrations/<version>/post-migrate.py`` -> runs on every ``-u``
    (post_init_hook does not run on upgrade).
"""

import logging

_logger = logging.getLogger(__name__)


def purge_web_assets(env):
    """Delete the compiled ``web.assets_*`` bundles so Odoo rebuilds the
    frontend CSS/JS from the current source files on the next request."""
    bundles = env["ir.attachment"].sudo().search([
        ("name", "=like", "web.assets_%"),
    ])
    count = len(bundles)
    bundles.unlink()
    _logger.info(
        "dashboard_rights: purged %s cached web.assets_* attachment(s); the "
        "frontend bundle will recompile from disk on next load.", count,
    )


def post_init_hook(env):
    purge_web_assets(env)
