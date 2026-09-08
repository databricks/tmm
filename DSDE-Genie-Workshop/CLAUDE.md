# CLAUDE.md — DSDE Genie Workshop

> **Last updated: 2026-09-08**
> When you load this file, compare that date to today. If it is **more than 30 days old**,
> remind Frank that this CLAUDE.md may be stale and offer to refresh it. Bump the date
> whenever you meaningfully change this file.

## What this project is

A hands-on, self-contained tutorial: **"AI-powered Analytics of 700 Million OpenSky Network
Avionics Records."** It teaches data scientists and data engineers how to get started with
**Databricks Genie** end to end, using real OpenSky Network flight telemetry rather than a
synthetic toy dataset.

The tutorial runs entirely on **Databricks Free Edition** and walks through: Marketplace →
Genie Agents (EDA) → Genie Agents (explore & visualize) → Genie Code for a Spark Declarative
Pipeline → Genie Code for a Databricks App → OpenSharing to a local OSS client → wrap-up.

## Goals

- **Free Edition, start to finish.** Every step must work on Free Edition — Unity Catalog +
  serverless, no paid features assumed. Call out Free Edition limits where they bite.
- **Real data, honest claims.** Real OpenSky telemetry; don't over-claim. Any metric shown must
  reflect what an attendee actually observes (see design decisions below).
- **Genie does the work.** Genie Agents do the analysis; Genie Code writes the SQL, pipeline,
  and app code. The narrative shows Genie generating artifacts from prompts.
- **Publishable docs.** The `docs/` tree is a MkDocs Material site deployed to GitHub Pages.

## Layout

- `README.md` — landing page / agenda / prerequisites.
- `docs/01..07-*.md` — the seven tutorial steps (ordered; nav lives in `mkdocs.yml`).
- `docs/assets/` — screenshots and intro GIFs referenced by the docs.
- `code/pipeline/`, `code/app/` — reference source for the Genie-generated pipeline and app
  (filled in during live-test against a real workspace).
- `code/opensharing/` — standalone local Delta Sharing client (pure Python, no Spark/Java).
- `mkdocs.yml` — site config **and the canonical page order** (reorder here, not by renaming).
- `.github/workflows/deploy.yml` — on push to `main`, runs `mkdocs gh-deploy` to GitHub Pages.

## Core design decisions

- **Canonical row count is 696 million / 696M** everywhere in prose. The title keeps the round
  "700 Million" deliberately. Don't reintroduce 700M/695.7M/695M in body text.
- **Voice: second person ("you"), not "we".** H1s are phrased as searchable questions for GEO.
  Every page carries the provenance footer `_Author: Frank Munz · Updated YYYY-MM-DD_`.
- **Docs prose vs. code are edited separately.** Style/GEO passes touch prose, headings, and
  front matter only — never code blocks, commands, or output. Keep that separation.
- **Honest metrics only.** Don't show a latency/performance number that a homegrown column
  fabricates or that the platform doesn't actually surface for the demo's setup. If a claim
  isn't measurable in the portable demo path, frame the step as mechanics, not a benchmark.
- **Prefer the reliable attendee path over the clever one.** For notebooks aimed at many
  attendees, favor `%pip install` + `dbutils.library.restartPython()` over PEP 723 inline
  metadata — PEP 723 on serverless still needs a manual **Apply** click on first attach.
- **OpenSharing step is intentionally OSS-only** — pure-Python `delta-sharing` client, no Spark
  and no Java, so it runs on a laptop from a `.share` credential file.

## Working in this repo

- This folder lives inside the `tmm` repo (`/Users/frank.munz/tmm`). **Commit directly to
  `main`; do not branch** — branch pushes trip a pre-existing secret-scan false positive.
  Never bypass the secret hook.
- Preview docs locally with `mkdocs serve` (deps in `requirements.txt`).
- Known stale references to fix opportunistically: `code/pipeline/README.md` and
  `code/app/README.md` still link to old step numbers (`03-pipeline.md`, `04-app.md`).
- Open TODOs (see `docs/CHANGELOG.md`): add missing screenshots `docs/assets/05-app.png` and
  `docs/assets/06-opensharing.png`.
