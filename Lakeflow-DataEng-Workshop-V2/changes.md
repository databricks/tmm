# Workshop changes — 2026-05-16 (Iceberg lab removed)

The Iceberg side-quest (previously Lab 6) was removed entirely from the workshop, and the
CI/CD via Declarative Automation Bundles lab moved from Lab 6 → Lab 5.

- `Labguide.md`: deleted the entire **Lab 5 — Iceberg side-quest** section (the CTAS, the
  PyIceberg reader, the `EXTERNAL USE SCHEMA` note, the `labs/05-Iceberg/` reference
  pointer). Renumbered the CI/CD lab heading to **Lab 5 — CI/CD via Declarative Automation
  Bundles**, and renumbered all six step headings `Step 6a` … `Step 6f` → `Step 5a` … `Step 5f`.
  Updated the overview list and the `prod_warehouse_id (Lab 6 only)` substitutions row.
- `labs/`: deleted `labs/05-Iceberg/` (both `global_sales_gold.sql` and
  `read_global_sales_gold.py`). Renamed `labs/06-DAB/` → `labs/05-DAB/`.
- `README.md`: dropped the **Managed Iceberg on Unity Catalog** bullet from "Technologies
  covered."
- `CLAUDE.md`: dropped the Lab 5 Iceberg project-overview entry; renumbered Lab 6 (DAB) →
  Lab 5; removed the Lab 5a/5b language-split entries (no Iceberg pipeline split to
  preserve); removed the `CREATE OR REPLACE TABLE` exemption (no longer needed without the
  Iceberg CTAS); renamed the **Lab 6 specifics** heading and body references to **Lab 5**;
  rewrote the files-in-this-repo entry — there is no `labs/05-Iceberg/`, and the renamed
  `labs/05-DAB/` is reserved as the local clone target only.
- Project overview opening line: "three optional/take-home labs" → "two optional/take-home
  labs."

The historical `changes.md` entries below describe an earlier review session against the
prior six-lab structure. They are kept for context; the bullets that mention Lab 5
(Iceberg) / Lab 6 (Iceberg) refer to that prior layout, not the current one.

---

# Workshop dry-run fixes — 2026-05-15

Applied during a single review session. Pre-existing folder rename (`lab1-bakehouse/` → `lab1/` etc., Iceberg moved from Lab 5 to Lab 6, RTM added as new Lab 5) was already staged in git; everything below is the content/correctness work that followed.

## Lab 1 — Bakehouse

- Dropped `TBLPROPERTIES('quality' = 'silver')` from both `lab1/sales_stats.sql` and the Lab 1 paste in `Labguide.md`. It's a free-form tag with no platform behavior — decorative in a 100-minute workshop.

## Lab 2 — Wanderbricks

- `lab2/booking_fraud_summary.sql` + matching reference block in `Labguide.md`:
  - Switched `booking_count`, `fraud_count`, and `fraud_pct` to `COUNT(DISTINCT b.booking_id)` / `COUNT(DISTINCT f.booking_id)`. Previously `COUNT(*)` after the join to `payments` (multi-row per booking) silently counted payment rows, not bookings, so the metrics meant the wrong thing.
  - Renamed CTE `fraud` → `fraud_bookings`.
  - Dropped the no-op `WHERE flag = 'fraud'` filter — the seed only writes `flag = 'fraud'`, so the filter never excluded anything. Volume is by definition a fraud-flag volume.
  - Dropped `TBLPROPERTIES('quality' = 'gold')` (same rationale as Lab 1).

## Lab 3 — DAB / Gourmet (`Labguide.md` only)

- **Added Step 3b item 4: dashboard catalog rename.** If students change `catalog_name` from `daiwt_gourmet` to `workshop` (item 1), they must also replace every occurrence of `daiwt_gourmet` in `resources/dashboard_gourmet_aibi.yml` and `src/aibi_dashboard.json`. Dashboard SQL is not parameterized by bundle variables, so skipping this leaves a dashboard pointing at a catalog the student doesn't have.
- **Fixed the CI/CD snippet.** `databricks bundle deploy -t prod` → `-t presenter`. The upstream Gourmet bundle has only one active target (`presenter`); `dev` is commented out and `prod` does not exist. Added explicit framing: production CI/CD setups would extend with `dev` and `prod` targets and pick one per branch.
- Updated the "Targets separate dev from prod" takeaway bullet to match the new framing.
- Added a troubleshooting-table row for the "dashboard renders empty after deploy" symptom pointing back to Step 3b item 4.
- **Did NOT change** the AI endpoint fallback names `databricks-claude-sonnet-4-5` / `databricks-claude-haiku-4-5` — the sub-agent claimed these were fabricated, but the official Databricks Foundation Model docs list both as real Claude endpoints.

## Lab 4 — Zerobus

- `lab4/send_temperature.py`:
  - OAuth `authorization_details` privilege strings switched from spaced form (`USE CATALOG`, `USE SCHEMA`) to underscore form (`USE_CATALOG`, `USE_SCHEMA`). Spaced form is SQL-grant syntax only; the OAuth payload requires the underscore form. Token exchange would have rejected the original payload as `invalid_authorization_details`.
  - Verify cell: replaced `where(f"city = '{CITY}'")` (string interpolation) with parameterized `where(col("city") == CITY)` — no SQL injection in a governance-themed lab.
- `Labguide.md`: rewrote the at-least-once claim. Zerobus REST is exactly-once at the protocol level (per-record ACK with idempotency); only client-side retry on transport errors makes the *system* at-least-once.

## Lab 5 — Real-Time Mode for SDP

This lab was over-corrected in the initial review. The reverts and corrections, conformant with the official RTM for SDP user guide:

- **Restored** `lab5/databricks.yml`: pipeline-level `configuration: spark.databricks.streaming.realTimeMode.enabled: "true"`. The RTM user guide names this as the required pipeline-level toggle (Step 2). The earlier review wrongly flagged it as a no-op.
- **Updated** `lab5/transformations/temperature_rtm.py` flow `spark_conf` to documented keys:
  - `pipelines.execution.realTimeMode: "true"` → `pipelines.trigger: "RealTime"`
  - `pipelines.realtime.trigger.duration: "60 second"` → `pipelines.trigger.interval: "1 minute"`
- **Reverted** Step 5d in `Labguide.md`: the toggle-off instruction is now back to setting `spark.databricks.streaming.realTimeMode.enabled` to `"false"` in `databricks.yml` — that is what the docs describe, and it actually disables RTM. The intermediate edit pointing at a non-documented flow-level key was wrong.
- **Did NOT add** any "RTM may fall back to micro-batch on unsupported sources" caveat — verified separately that this doesn't happen with the `rate` source in this lab.

## Lab 6 — Iceberg (renumbered from Lab 5)

- `lab6/global_sales_gold.sql`: header comment `Step 1c` → `Lab 6, Step 6a`. Placeholder `workshop.<user>.…` → `workshop.USER_ID.…` (two occurrences) to match the guide's convention.
- `lab6/read_global_sales_gold.py`: header `Lab 1, Step 1d` → `Lab 6, Step 6b`. `SCHEMA = "<user>"` → `"USER_ID"`.
- `Labguide.md`: leftover step labels `Step 5a` / `Step 5b` → `Step 6a` / `Step 6b`. Wording "5 cities" → "5 (city, country) pairs" to match `GROUP BY city, country LIMIT 5` (the same city in two countries would count twice).

## README.md

- Course arc bullet count: "four core labs plus one optional side-quest" → "four core labs plus two optional take-home labs" to reflect the new Lab 5 (RTM).
- Folder links refreshed: `lab1-bakehouse/` → `lab1/`, `lab2-wanderbricks/` → `lab2/`, `lab4-zerobus/` → `lab4/`, `lab5-iceberg/` → `lab6/`.
- Added a Lab 5 RTM bullet pointing at `lab5/`.
- Renumbered Iceberg to Lab 6.

## CLAUDE.md

- Project overview rewritten for the six-lab structure (was four-core + one-optional, now four-core + two-optional). Added a complete Lab 5 (RTM) entry; rewrote Lab 6 entry; refreshed all folder paths.
- Lab 3 entry: replaced the `databricks bundle deploy -t prod` framing with "the upstream demo bundle has only `presenter`; production CI/CD would extend with `dev` and `prod` targets."
- Lab 4 entry: added the OAuth-privilege underscore-form note (`USE_CATALOG`, `USE_SCHEMA`, `SELECT`, `MODIFY`).
- Language-split section: renumbered `Lab 5a` / `Lab 5b` → `Lab 6a` / `Lab 6b`; added a Lab 5 (RTM, Python) entry; clarified that the in-pipeline language split applies to the core arc (Labs 1–4), not the take-home labs.
- SDP code-conventions section: the `CREATE OR REPLACE TABLE` exemption now references Lab 6 (not Lab 5).
- Setup-notebook responsibilities section: added the OAuth underscore-form note alongside the SP-grants list.
- Files-in-this-repo section: every folder path refreshed; added a `lab5/` entry describing the RTM bundle.

## Things deliberately NOT changed

These were flagged by the sub-agents but are either unverifiable or were wrong-call:

- **Zerobus REST URL shape and OAuth audience** (`{_ENDPOINT}/zerobus/v1/tables/.../insert`, `api://databricks/workspaces/{id}/zerobusDirectWriteApi`) — sub-agent couldn't verify against live Databricks Zerobus REST docs. Worth confirming against the current Beta reference before the live demo.
- **`setup_workshop.py:231-235` SP credentials POST** — sub-agent flagged the workspace-host vs. account-host as a likely 401/403, but the in-code comment shows the original author chose this path deliberately around an SDK gap. Leaving for verification against a working setup, since Lab 5 already proved the sub-agents can be wrong about "this won't work."
- **PyIceberg version pin** `pyiceberg>=0.9,<0.10`, `pyarrow<20` in `lab6/read_global_sales_gold.py` — judgment call; current pin works for the workshop's read-only use case.
- **AI endpoint fallback names** in Lab 3 (`databricks-claude-sonnet-4-5` / `databricks-claude-haiku-4-5`) — verified against the Databricks Foundation Model docs; both are real endpoints.
- **`setup_workshop.py`** — was already showing as modified at session start; no edits made during this work.
