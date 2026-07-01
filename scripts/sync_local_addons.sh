#!/usr/bin/env bash
#
# sync_local_addons.sh — stage all custom Odoo addons into the web container's
# container-local addons dir (/tmp/local-addons), then rebuild the asset bundles.
#
# WHY THIS EXISTS
# ----------------
# This repo lives under an iCloud Drive path
# (~/Library/Mobile Documents/com~apple~CloudDocs/...). Docker Desktop / colima
# share that path into the Linux VM via a bind mount, and concurrent reads of
# many files from that mount intermittently fail with
#   OSError: [Errno 35] Resource deadlock avoided   (EDEADLK)
# Odoo hits this during (a) Python module import on registry load and
# (b) SCSS/JS asset-bundle compilation, because both read many files at once.
# The symptoms are: modules silently fail to load, the JS bundle ships without
# `web.session` / `GridStack`, and the CSS bundle ships a `css_error_message`
# rule ("A css error occured, using an old style to render this page").
#
# Reads from the HOST filesystem work fine; only the in-VM bind mount deadlocks.
# So we copy every custom module from the host into a container-local directory
# (/tmp/local-addons, already first in addons_path) using `tar | docker exec`,
# which streams through the Docker CLI on the host. Odoo then reads code from
# the local copy and never touches the deadlocking mount during load/compile.
#
# The heavy `static/description/` image dirs are excluded — they are only served
# on demand (never read during load/compile) and bloat the copy.
#
# WHEN TO RUN
# -----------
#   * After `docker compose up` / `down && up` (a fresh container has an empty
#     /tmp/local-addons).
#   * Any time you see the GridStack / web.session / "old style" CSS errors.
#
# PERMANENT FIX (makes this script unnecessary): move the repo off iCloud Drive
# to a plain path (e.g. ~/Projects/cloud) and update the bind mount in
# docker-compose.yml. Then /mnt/extra-addons reads cleanly and Odoo needs no
# local staging.
#
# Usage:
#   scripts/sync_local_addons.sh [--no-restart]
#
# Env overrides (defaults match this project's docker-compose):
#   WEB_CONTAINER=cloud-web-1  DB_CONTAINER=cloud-db-1  DB_NAME=dbcloud
#   DB_USER=odoo  DB_PASSWORD=odoo  LOCAL_ADDONS=/tmp/local-addons
#
set -euo pipefail

WEB_CONTAINER="${WEB_CONTAINER:-cloud-web-1}"
DB_CONTAINER="${DB_CONTAINER:-cloud-db-1}"
DB_NAME="${DB_NAME:-dbcloud}"
DB_USER="${DB_USER:-odoo}"
DB_PASSWORD="${DB_PASSWORD:-odoo}"
LOCAL_ADDONS="${LOCAL_ADDONS:-/tmp/local-addons}"
RESTART=1
[[ "${1:-}" == "--no-restart" ]] && RESTART=0

# Repo root = parent of this script's directory.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Repo:          $REPO_ROOT"
echo "==> Web container: $WEB_CONTAINER"
echo "==> Target:        $WEB_CONTAINER:$LOCAL_ADDONS"

if ! docker inspect "$WEB_CONTAINER" >/dev/null 2>&1; then
  echo "ERROR: container '$WEB_CONTAINER' not found. Start it with: docker compose up -d" >&2
  exit 1
fi

docker exec --user root "$WEB_CONTAINER" mkdir -p "$LOCAL_ADDONS"

# Collect every top-level module directory (has __manifest__.py).
# Plain loop (no mapfile) so this works on macOS's stock bash 3.2.
MODULES=""
for d in */; do
  [ -f "${d}__manifest__.py" ] && MODULES="$MODULES ${d%/}"
done
# shellcheck disable=SC2086
set -- $MODULES
total=$#
echo "==> $total custom modules found."

echo "==> Staging all custom modules in a single tar stream..."
tar \
  --exclude='static/description' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  -cf - $MODULES 2>/dev/null \
| docker exec --user root -i "$WEB_CONTAINER" \
    tar -xf - -C "$LOCAL_ADDONS" 2>/dev/null || {
      echo "      ERROR: failed to stage modules" >&2
      exit 1
    }

docker exec --user root "$WEB_CONTAINER" chown -R odoo:odoo "$LOCAL_ADDONS"
echo "==> Staging complete."

# Drop cached asset bundles so they recompile from the freshly-staged code.
echo "==> Clearing cached asset bundles..."
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c \
  "delete from ir_attachment where name like 'web.assets%' or name like '%ks_dashboard%';" >/dev/null
# Bump the registry signal so the running worker reloads on next request.
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tc \
  "select nextval('base_registry_signaling');" >/dev/null

if [[ "$RESTART" == "1" ]]; then
  echo "==> Restarting $WEB_CONTAINER so bundles recompile clean..."
  docker restart "$WEB_CONTAINER" >/dev/null
  echo -n "==> Waiting for Odoo"
  for _ in $(seq 1 18); do
    code="$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8069/web/login || true)"
    if [[ "$code" == "200" || "$code" == "303" ]]; then echo " — up."; break; fi
    echo -n "."; sleep 5
  done
fi

echo "==> Done. Hard-reload the browser (Cmd-Shift-R) to fetch fresh bundles."
