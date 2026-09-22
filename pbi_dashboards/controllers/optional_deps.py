# -*- coding: utf-8 -*-
"""Third-party packages a dashboard can do without.

The pbi modules must INSTALL AND LOAD on a server that does not have every
optional package — a PowerPoint export is a convenience on two boards, not a
reason for the whole dashboard suite to be uninstallable. So no pbi manifest
declares external_dependencies (Odoo refuses to install a module whose
declared dependency is missing), and every ``import pptx`` sits behind a
guard that records what is available instead of raising at import time.

What each board then does with that:

  * the capability dict travels to the browser with the board's own data
    (and is available on its own at /pbi_dashboards/capabilities), so a
    control whose package is missing renders disabled, with a message naming
    the package rather than a button that fails when pressed;
  * the routes behind those controls check again on the server, because a
    disabled button is a courtesy and not a guarantee — a direct request
    gets the same message rather than an ImportError traceback.

Availability is probed once, when this module is imported, which is also
when the guarded imports in the export code run. Installing the package on a
running server therefore takes effect at the next Odoo restart, and the
message says so; the dashboards need no code change to pick it up.

PDF export is deliberately NOT in here as a server capability: every "Export
PDF" button in these dashboards calls window.print(), so it needs nothing
installed and cannot become unavailable. It is reported as always-available
so a board can render both export controls through one uniform check.
"""
import importlib
import os
import site
import sys


def _ensure_user_site():
    """Ensure user site-packages is on sys.path even in virtualenvs."""
    try:
        user_site = site.getusersitepackages()
        if user_site and user_site not in sys.path and os.path.isdir(user_site):
            sys.path.append(user_site)
    except Exception:
        pass


def _probe(module_name):
    if not module_name:
        return True
    _ensure_user_site()
    try:
        importlib.invalidate_caches()
        importlib.import_module(module_name)
    except Exception:
        return False
    return True


PPTX_PACKAGE = "python-pptx"
PPTX_PIN = "0.6.23"          # matches cloud/Dockerfile
PPTX_AVAILABLE = _probe("pptx")

# The xlsx export on the Service boards. Same contract as pptx: the route that
# builds the workbook imports it behind a guard, and the CSV route beside it
# needs nothing installed, so an absent openpyxl costs the formatted sheet and
# nothing else. Registered here so the Configurations page can report and
# install it through the one mechanism that never takes a package name from a
# request -- a key is looked up in this dict, and only what is in this dict
# can ever reach pip.
XLSX_PACKAGE = "openpyxl"
XLSX_PIN = "3.1.2"           # matches cloud/Dockerfile
XLSX_AVAILABLE = _probe("openpyxl")


def is_pptx_available():
    """Live probe so dynamic installations are detected without waiting for server reboot."""
    return _probe("pptx")


def is_xlsx_available():
    """Live probe for openpyxl, for the same reason is_pptx_available exists."""
    return _probe("openpyxl")


def capabilities():
    """What the browser needs to decide which export controls to offer.

    Sent as-is to the client; keep it JSON-serialisable and keep the shape
    stable — every board's JS reads the same keys."""
    pptx_ok = is_pptx_available()
    xlsx_ok = is_xlsx_available()
    return {
        "pptx": {
            "available": pptx_ok,
            "feature": "PowerPoint export",
            "package": PPTX_PACKAGE,
            # The IMPORT name, which is not the install name -- "pip3 install
            # python-pptx" gives you "import pptx". Carried here so anything
            # that wants to re-probe (the Configurations page does, to tell
            # "not installed" apart from "installed, awaiting a restart") reads
            # it from the one place that knows rather than repeating it.
            "module": "pptx",
            # Pinned to what the Dockerfile installs, so a server that gets the
            # package from the Configurations button ends up on the same version
            # as one built from the image.
            "pin": PPTX_PIN,
            "install": "pip3 install %s==%s" % (PPTX_PACKAGE, PPTX_PIN),
            "restartRequired": not pptx_ok,
            "message": pptx_unavailable_message(),
        },
        "xlsx": {
            "available": xlsx_ok,
            "feature": "Excel (.xlsx) export",
            "package": XLSX_PACKAGE,
            # Install name and import name happen to agree here, unlike pptx.
            # Carried anyway, because whatever re-probes reads this key and
            # must not have to know which packages are the lucky ones.
            "module": "openpyxl",
            "pin": XLSX_PIN,
            "install": "pip3 install %s==%s" % (XLSX_PACKAGE, XLSX_PIN),
            "restartRequired": not xlsx_ok,
            "message": xlsx_unavailable_message(),
        },
        "pdf": {
            # window.print() in the browser — nothing to install, ever.
            "available": True,
            "feature": "PDF export",
            "package": None,
            "module": None,
            "pin": None,
        },
    }


def pptx_unavailable_message():
    if is_pptx_available():
        return ""
    return (
        "PowerPoint export is unavailable on this server: the %s package is "
        "not installed. Install it with \"pip3 install %s==%s\" and restart Odoo, "
        "and this button turns itself back on. Export PDF needs nothing "
        "installed and works now." % (PPTX_PACKAGE, PPTX_PACKAGE, PPTX_PIN)
    )


def xlsx_unavailable_message():
    if is_xlsx_available():
        return ""
    return (
        "Excel export is unavailable on this server: the %s package is not "
        "installed. Install it with \"pip3 install %s==%s\" and restart Odoo, "
        "and this button turns itself back on. Export CSV needs nothing "
        "installed and works now." % (XLSX_PACKAGE, XLSX_PACKAGE, XLSX_PIN)
    )
