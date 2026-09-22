# These are the real files; `scripts/` points here

Every `.sql` in this directory is a real file, and the repository's top-level
`scripts/` holds a relative symlink back to it:

    scripts/ac_scope_data_fixes_portable.sql -> ../pbi_dashboard_configurations/sql/ac_scope_data_fixes_portable.sql

There is still exactly ONE copy of every script, so nothing can drift. Only the
direction changed.

## Why it points this way round

It used to be the other way: real files in `scripts/`, symlinks here. That
assumed the Odoo addons path is the repository root, which is true of both
servers this suite runs on -- until someone deploys the module folder on its
own, which is the ordinary way to ship one module. Then all nineteen links
dangle at once and every card on the Configurations page fails with

    The script file <name>.sql could not be read on this server:
    [Errno 2] No such file or directory

Hit for real on staging-hhsv3 on 2026-09-11, having been predicted in this very
file and left unfixed because the only remedies considered were "deploy the
whole repository" and "keep two copies and accept the drift".

Flipping the direction has neither cost. The module is self-contained, so
deploying just the module works. `psql -f scripts/<name>.sql` still works,
because the symlink resolves inside a full checkout. And there is still one
file, so the drift argument that motivated symlinks in the first place still
holds.

## What each side now assumes

- **This module**: nothing. `sql/` is real files inside the module. A deploy
  that copies this folder carries the scripts with it, symlink support or not.
- **`scripts/`**: that the module sits beside it in a full checkout. That is
  only true in the repository, which is the only place `scripts/` is used --
  it is the shell entry point, referenced from commit messages and from
  `docs/erp_master_data_defects.html`.

`controllers/scripts.py` keeps a fallback that looks in `<addons root>/scripts/`
when a file is not here, so a checkout that still has the old layout, or a copy
made by a tool that dereferenced the links, keeps working either way.

## Adding a script

Put the real file HERE, symlink it from `scripts/`, and add an entry to
`SCRIPTS` in `controllers/scripts.py`. The dict is the allow-list: a key that is
not in it is refused before the filesystem is touched, so a file sitting here
unreferenced does nothing.
