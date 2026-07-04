#!/usr/bin/env bash
#
# One-shot deploy for the /tmp/local-addons staging setup (Option C).
#
# Why this exists: Odoo's addons_path starts with /tmp/local-addons, and the
# dist-packages copies of the custom modules are symlinks INTO that dir (see
# Dockerfile). The repo is only bind-mounted read-only at /mnt/extra-addons and
# is NOT on the addons_path, so `git pull` alone changes nothing that Odoo loads
# — the code must be re-staged (copied) into /tmp/local-addons. This script does
# pull -> re-stage -> purge stale asset bundle -> upgrade -> restart, in order,
# so a deploy can't be half-done.
#
# Usage (run from the repo root on the server, where docker-compose.yml lives):
#     ./scripts/deploy_update.sh [DB] [MODULE ...]
#     ./scripts/deploy_update.sh dbprod dashboard_rights          # targeted (fast)
#     ./scripts/deploy_update.sh dbprod --full-stage dashboard_rights
#         ^ re-stage EVERY module (needed after `compose down/up`, which wipes
#           /tmp/local-addons), then upgrade only the listed module(s).
#
# Defaults: DB=dbprod, MODULE=dashboard_rights.
#
set -euo pipefail

DB="${1:-dbprod}"; shift || true

FULL_STAGE=0
if [[ "${1:-}" == "--full-stage" ]]; then
  FULL_STAGE=1; shift || true
fi

MODULES=("$@")
[[ ${#MODULES[@]} -eq 0 ]] && MODULES=(dashboard_rights)

BRANCH="copilot/vscode-mqqb6g5l-9g4e"
REMOTE="personal"

# The working remote is 'personal'; 'origin' (Penygonarabia) is dead. Add it if
# the server's checkout only knows origin.
if ! git remote | grep -qx "$REMOTE"; then
  echo ">> remote '$REMOTE' missing — add it, e.g.:"
  echo "     git remote add $REMOTE git@github.com:sswar2000/hhs_cloud.git"
  echo "   (or the https://<token>@github.com/... form) then re-run."
  exit 1
fi

dc() { docker compose "$@"; }

echo ">> 1/5 Pull latest ($REMOTE/$BRANCH)"
git pull "$REMOTE" "$BRANCH"

echo ">> 2/5 Re-stage into /tmp/local-addons"
if [[ $FULL_STAGE -eq 1 ]]; then
  # Whole repo -> staging (excludes VCS/pyc). Needed after a container recreate.
  dc exec -u root -T web sh -c '
    mkdir -p /tmp/local-addons &&
    cp -a /mnt/extra-addons/. /tmp/local-addons/ &&
    rm -rf /tmp/local-addons/.git &&
    find /tmp/local-addons -name "__pycache__" -type d -prune -exec rm -rf {} + ;
    echo "   full stage complete"'
else
  for m in "${MODULES[@]}"; do
    dc exec -u root -T web sh -c "
      rm -rf /tmp/local-addons/$m &&
      cp -a /mnt/extra-addons/$m /tmp/local-addons/$m &&
      find /tmp/local-addons/$m -name '__pycache__' -type d -prune -exec rm -rf {} + ;
      echo '   staged $m'"
  done
fi

echo ">> 3/5 Purge stale web.assets bundle (forces CSS/JS recompile)"
dc exec -T db psql -U odoo -d "$DB" -c \
  "DELETE FROM ir_attachment WHERE name LIKE 'web.assets_%';"

echo ">> 4/5 Upgrade module(s): ${MODULES[*]}"
CSV=$(IFS=,; echo "${MODULES[*]}")
dc exec -T web odoo -u "$CSV" -d "$DB" --stop-after-init

echo ">> 5/5 Restart web (preserves /tmp/local-addons; recreate would wipe it)"
dc restart web

echo ">> Done. Hard-reload the browser (Cmd/Ctrl-Shift-R) to drop the cached bundle."
