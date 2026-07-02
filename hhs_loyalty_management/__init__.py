import sys
import os

# ──────────────────────────────────────────────────────────────
# Inject extra Python library path at import time.
# This runs when Odoo scans/loads addons from hhs_cloud_001.
# ──────────────────────────────────────────────────────────────
_EXTRA_LIB_PATH = os.path.join('D:', os.sep, 'Installation_Folder', 'python_libs')
if os.path.isdir(_EXTRA_LIB_PATH) and _EXTRA_LIB_PATH not in sys.path:
    sys.path.insert(0, _EXTRA_LIB_PATH)

from . import models
from . import wizard
from . import report
