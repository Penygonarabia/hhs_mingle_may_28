# Contract Phase 2 — Service & Repair

Lead-driven, **non-AMC** repair flow: one customer enquiry (5–10 AC units) →
many job cards → **one** consolidated quotation → **one** invoice.

## Architecture

- **Self-contained:** every `service_repair` / `cp2_*` line lives in this module,
  done via overrides. One exception: `machine_repair_management`'s `project.task.write`
  exempts `job_card_type == 'service_repair'` from the mandatory Unit Name Plate
  photo when reaching *Customer Need Quote* (that validation can't be overridden
  from a subclass without breaking the base state-sync).
- **Not standalone:** it is an *extension*. It reuses the existing job-card engine
  rather than reimplementing it, so it depends on:
  `machine_repair_management`, `hyperbill_payments`, `crm`.

### Models

| Model | Kind |
|---|---|
| `contract.phase2.technician.line` | **new** — the lead's technician grid row |
| `crm.lead` | inherited — Service & Repair lead fields + job-card generation |
| `project.task` | inherited — job cards: `job_card_type`, payment flags, S&R fixes |
| `service.sale.order` | inherited — populate / confirm / single invoice |
| `account.move` | inherited — `cp2_quotation_id` (invoice → quotation link) |

## Flow

1. **Lead** (`crm.lead`, `is_service_repair`): inspection payment + technician grid → **Create Job Cards**.
2. **Job cards** (`project.task`, type `service_repair`): parts + service; no per-card quote/invoice.
3. **Quotation** (`service.sale.order`): **Populate from Job Cards** → **Confirm Quotation**.
4. **Payment** (Hyperpay) → propagated to the job cards.
5. **Invoice**: one consolidated `account.move` via **Create Invoice**.

## Design note — work-center exemptions

Service & Repair cards intentionally have **no work center**, which trips several
base `machine_repair_management` behaviours. This module exempts `service_repair`
cards from each (all in `models/job_card.py` / views):

- `search_fetch` — list visibility (work-center/AMC scoping bypassed)
- `include_zero_stock_bool` — quote parts without technician-warehouse stock
- `_compute_warehouse_lst_ids` — skip technician-warehouse validation on assignment
- Technician (team) selector domain relaxed to all teams
- Per-card **Create Quotation** / **Send Proforma Invoice** hidden (consolidated instead)
