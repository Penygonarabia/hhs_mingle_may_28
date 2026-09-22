#!/usr/bin/env bash
#
# One-shot deploy: pull -> re-stage (if needed) -> purge stale asset bundle ->
# upgrade -> restart, in order, so a deploy can't be half-done.
#
# TWO ARRANGEMENTS EXIST, AND THIS SCRIPT ASKS WHICH ONE IT IS ON.
#
# It was written for the /tmp/local-addons staging setup (Option C): Odoo's
# addons_path started with /tmp/local-addons, the dist-packages copies of the
# custom modules were symlinks INTO that dir (see Dockerfile), and the repo was
# bind-mounted read-only at /mnt/extra-addons and NOT on the addons_path — so
# `git pull` alone changed nothing Odoo loads and the code had to be copied in.
# That existed to dodge an EDEADLK on an iCloud-backed bind mount;
# sync_local_addons.sh's header tells the whole story.
#
# The permanent fix that header describes — move the repo to a plain path and
# point the mount at it — has since been applied on at least one host, where
# addons_path is just /mnt/extra-addons and NOTHING reads /tmp/local-addons.
#
# Hard-coding either arrangement would be wrong on the other host, so step 2
# reads addons_path out of the RUNNING CONTAINER and stages only when the
# staging dir is genuinely on it. Copying into a directory nothing reads is the
# quiet kind of wrong: it runs, it succeeds, and it changes nothing.
#
# Usage (run from the repo root on the server, where docker-compose.yml lives):
#     ./scripts/deploy_update.sh [DB] [MODULE ...]
#     ./scripts/deploy_update.sh dbprod module_rights          # targeted (fast)
#     ./scripts/deploy_update.sh dbprod --full-stage module_rights
#         ^ re-stage EVERY module (needed after `compose down/up`, which wipes
#           /tmp/local-addons), then upgrade only the listed module(s).
#
# Defaults: DB=dbprod, MODULE=module_rights.
#
set -euo pipefail

DB="${1:-dbprod}"; shift || true

FULL_STAGE=0
if [[ "${1:-}" == "--full-stage" ]]; then
  FULL_STAGE=1; shift || true
fi

MODULES=("$@")
[[ ${#MODULES[@]} -eq 0 ]] && MODULES=(module_rights)

# The branch to deploy. main by default; override for a server that is meant to
# track something else:
#
#     DEPLOY_BRANCH=some-branch ./scripts/deploy_update.sh dbprod pbi_sales_dashboards
#
# It was pinned to a long-dead feature branch, which meant step 1 pulled a
# branch that had not moved in months and every later step then re-staged,
# upgraded and restarted on code nobody had changed -- a deploy that reported
# success and shipped nothing. Defaulting to main is what makes "run the deploy
# script" mean what it says.
BRANCH="${DEPLOY_BRANCH:-main}"
REMOTE="${DEPLOY_REMOTE:-personal}"
STAGING_DIR="${DEPLOY_STAGING_DIR:-/tmp/local-addons}"

# WHETHER THERE IS ANYTHING TO PULL FROM.
#
# The working remote is 'personal'; 'origin' (Penygonarabia) is dead.
#
# A checkout with NO remote at all is a legitimate deploy source — the laptop
# checkouts are exactly that, and code reaches them by commit rather than by
# fetch. What is not legitimate is deploying one silently: that is the same
# failure the branch pinning caused, five green steps and nothing shipped. So a
# remoteless checkout deploys the WORKING TREE and says so in those words,
# naming the commit, and naming any uncommitted changes riding along with it.
#
# A checkout that HAS remotes but not this one stays an error: something was
# configured and the name does not match, and guessing which is not this
# script's call.
if [[ -z "$(git remote)" ]]; then
  PULL=0
elif git remote | grep -qx "$REMOTE"; then
  PULL=1
else
  echo ">> remote '$REMOTE' missing. This checkout has: $(git remote | tr '\n' ' ')"
  echo "   Add it, e.g.:"
  echo "     git remote add $REMOTE git@github.com:sswar2000/hhs_cloud.git"
  echo "   (or the https://<token>@github.com/... form), or set DEPLOY_REMOTE."
  exit 1
fi

dc() { docker compose "$@"; }

if [[ $PULL -eq 1 ]]; then
  echo ">> 1/5 Pull latest ($REMOTE/$BRANCH)"
  git pull "$REMOTE" "$BRANCH"
else
  echo ">> 1/5 No git remote configured — deploying THIS WORKING TREE, not a fetch"
  echo "        commit: $(git rev-parse --short HEAD)  $(git log -1 --format=%s | cut -c1-58)"
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "        NOTE: tree is dirty. The uncommitted changes below WILL deploy:"
    git status --short | head -10 | sed 's/^/              /'
  fi
fi

# Ask the CONTAINER which arrangement it is running, rather than assuming (see
# the header). Staging into a directory nothing reads would report success and
# ship nothing, which is precisely the class of failure this script exists to
# prevent.
ADDONS_PATH="$(dc exec -T web sh -c \
  'grep -hE "^[[:space:]]*addons_path" /etc/odoo/odoo.conf 2>/dev/null | head -1' \
  2>/dev/null | tr -d '\r')"

if [[ "$ADDONS_PATH" != *"$STAGING_DIR"* ]]; then
  echo ">> 2/5 Re-stage — SKIPPED: $STAGING_DIR is not on addons_path"
  if [[ -n "$ADDONS_PATH" ]]; then
    echo "        ${ADDONS_PATH## }"
  else
    echo "        (addons_path unreadable; assuming the bind mount is live)"
  fi
  echo "        Odoo reads the bind mount directly, so the code is already in place."
elif [[ $FULL_STAGE -eq 1 ]]; then
  echo ">> 2/5 Re-stage into $STAGING_DIR (full)"
  # Whole repo -> staging (excludes VCS/pyc). Needed after a container recreate.
  dc exec -u root -T web sh -c "
    mkdir -p $STAGING_DIR &&
    cp -a /mnt/extra-addons/. $STAGING_DIR/ &&
    rm -rf $STAGING_DIR/.git &&
    find $STAGING_DIR -name '__pycache__' -type d -prune -exec rm -rf {} + ;
    echo '   full stage complete'"
else
  echo ">> 2/5 Re-stage into $STAGING_DIR"
  for m in "${MODULES[@]}"; do
    dc exec -u root -T web sh -c "
      rm -rf $STAGING_DIR/$m &&
      cp -a /mnt/extra-addons/$m $STAGING_DIR/$m &&
      find $STAGING_DIR/$m -name '__pycache__' -type d -prune -exec rm -rf {} + ;
      echo '   staged $m'"
  done
fi

echo ">> 3/5 Purge stale web.assets bundle (forces CSS/JS recompile)"
dc exec -T db psql -U odoo -d "$DB" -c \
  "DELETE FROM ir_attachment WHERE name LIKE 'web.assets_%';"

echo ">> 4/5 Upgrade module(s): ${MODULES[*]}"
CSV=$(IFS=,; echo "${MODULES[*]}")
dc exec -T web odoo -u "$CSV" -d "$DB" --stop-after-init

echo ">> 5/5 Restart web (restart preserves $STAGING_DIR; a recreate would wipe it)"
dc restart web

echo ">> Done. Hard-reload the browser (Cmd/Ctrl-Shift-R) to drop the cached bundle."
