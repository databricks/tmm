# GEO & Writing-Style Review — Changelog (2026-09-04)

Applied by the `geo-writing-review` skill. Prose, headings, and front-matter only —
**no code blocks, commands, or output were changed**. Cross-cutting item #3 (gold
tables vs. gold materialized views wording) was intentionally skipped per author.
Canonical row count set to **696 million** across all pages.

## README.md
- GEO: added author + updated-date provenance footer.
- GEO: row count → "696 million" (title keeps the round "700 Million").
- Style: stripped trailing whitespace.

## docs/01-marketplace.md
- Style: first-person → second person ("What we do" → "What you'll do"; "We attach … our workspace" → "You attach … your workspace").
- Style: removed stray orphan line "Databricks Marketplace" above the image.
- GEO: H1 → searchable question ("How do I get the OpenSky dataset from Databricks Marketplace?").
- GEO: row count → "696 million rows".
- GEO: added provenance footer.

## docs/02-genie-eda.md
- GEO: **fixed broken `[!TIP]` callout** (added missing `>` so it renders).
- Style: removed empty `##` heading.
- Style: fixed typo "ica024" → "icao24" (prose only; code untouched).
- Style: fixed unclosed parenthesis in Step 1.
- Style: "What we do" → "What you'll do".
- GEO: H1 → searchable question.
- GEO: row count in caption → "696M records".
- GEO: added provenance footer.

## docs/03-genie-explore.md
- Style: first-person → second person ("What we do" → "What you'll do"; "we now use" → "you now use").
- Style: split one 60-word sentence into shorter, active sentences.
- Style: removed stray `**` (broken bold marker).
- GEO: H1 → searchable question.
- GEO: added provenance footer.

## docs/04-pipeline.md
- Style: first-person → second person ("We turn/generate" → "You turn/generate"; "we reduce" → "you reduce").
- Style: removed empty `##` heading.
- GEO: H1 → searchable question.
- GEO: row count → "close to 696 million records".
- GEO: added provenance footer.
- NOTE (not applied, per author): gold "tables" vs "materialized views" wording left as-is.

### 2026-09-04 second pass (Genie/SDP intro + dash/AI-tell cleanup)
- Added a two-sentence problem→resolution intro after the H1 (SDP handles the mechanics, Genie Code generates it from a prompt).
- Fixed typos: "a a working" → "a working"; "a eeper" → "a deeper"; broken "Lakeflow. See" → "…Lakeflow, see".
- Heading grammar: "Step-by-step guide Apache SDP with Genie Code" → "Step-by-step guide: Apache SDP with Genie Code".
- Repaired the intro note: pulled the orphaned "That tutorial…" line back into the paragraph, "we focus" → "you focus".
- Converted the step blockquote into a real ordered list (matches pages 01–03); prompt code block and Step 3/4 bullets kept verbatim.
- Heading hierarchy: "Medallion Architecture" and "Pipeline Graph" demoted to `###` under Results; added missing blank line.
- Removed em dashes across intro note, Results, silver, gold, recap, and two image alt strings (colon / comma / parenthetical). Coordinate minus signs and numeric ranges left intact.
- Added link to Free Edition limitations; added the "we deliberately go the easy way" subsampling aside.
- NOTE (not applied): the `[Step 3]`/`[Step 4]` links use `#step-by-step-guide`, which does not match the auto-generated anchor for that heading (pre-existing; unchanged by this pass).

## docs/05-app.md
- Style: first-person → second person ("We build/zoom" → "You build/zoom").
- GEO: H1 → searchable question.
- GEO: row count → "696M" (two spots).
- GEO: added provenance footer.
- TODO (cannot auto-apply): add screenshot `docs/assets/05-app.png` — placeholder left in place.

## docs/06-genie-one.md — REMOVED
- The Genie One step was removed from the tutorial. Deleted `docs/06-genie-one.md`, dropped it from the README agenda and flow diagram and from the wrap-up recap, and rewired nav so the Databricks App (5) links straight to OpenSharing.
- Renumbered the remaining steps: OpenSharing 07 → 06, Wrap-up 08 → 07 (files renamed; titles, nav, and all cross-references updated).

## docs/06-opensharing.md (was 07)
- Style: first-person → second person ("Now we go / because we read / we push / We don't want" → "you" forms). One "we convert" left inside a code-comment-adjacent explanation of the snippet.
- GEO: H1 → searchable question.
- GEO: row count → "696M" (three spots).
- GEO: added provenance footer.
- TODO (cannot auto-apply): add screenshot `docs/assets/06-opensharing.png` — placeholder left in place.

## docs/07-wrap-up.md (was 08)
- Style: "What we did" → "What you did".
- GEO: added provenance footer.

## Cross-page fixes
- Terminology/consistency: standardized row count on **696 million / 696M** everywhere (was 700M / 695.7M / 695M).
- Provenance: uniform `_Author: Frank Munz · Updated 2026-09-04_` footer on every page.
- Voice: converted first-person "we" to second-person "you" across all pages to match the target voice.

## Still open (author action needed)
- Add the 2 missing screenshots (05-app, 06-opensharing) — these cap those pages' projected GEO score.
- Optional: add a one-line key-facts block to the README (not applied).
