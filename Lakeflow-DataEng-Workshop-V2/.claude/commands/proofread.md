---
description: Style + grammar review of the workshop lab guide. Emits a batch report grouped by importance; never modifies the file and never touches step-by-step instructions.
argument-hint: [file-path]
---

You are reviewing **$ARGUMENTS** as a technical-writing editor for the Lakeflow Data Engineering Workshop. If `$ARGUMENTS` is empty, default to `./Labguide.md`.

## Hard scope rule

**Only edit prose that *describes* the labs — never the instructions.** Instructions are the workshop's contract with the attendee; rewording them risks breaking the lab.

**Off-limits — do not propose edits inside these regions:**
- Anything telling the attendee a command to run or a place on the UI to click. This includes numbered step lists, "Workspace sidebar → …" navigation chains, every CLI invocation, and inline UI element names in **bold** within instructional sentences.
- All fenced code blocks (```bash, ```python, ```sql, ```yaml, ```text, etc.) and inline `code` spans.
- All Markdown tables (substitutions, troubleshooting, basic-command set, etc.).
- All callout blockquotes (lines starting with `>`), e.g. `> **Optional**`, `> **Retargeting is mandatory**`, `> Reference …`.
- The `## References and other demos` section — link text matches upstream titles; do not rephrase.

**Fair game:**
- Lab and section opening prose ("In this lab you'll …", "Lab 3 flips the script …").
- "Key teaching points", "What to take away", "Lab N take-away" lists.
- Standalone explanatory paragraphs *between* steps.
- Section transitions and framing sentences.

If unsure whether a paragraph is instruction or description, leave it alone.

## Edit conservatively (default bias)

The lab guide already works. Your job is polish, not rewrite.

- **Stay as close to the original as possible.** Prefer the smallest change that fixes the issue. Reuse the original wording wherever you can; don't rephrase a sentence just because you'd phrase it differently.
- **Keep the narrative short, not chatty.** If a proposed rewrite is *longer* than the original, treat that as a red flag and reconsider — tightening should shrink prose, not grow it. Cuts beat replacements.
- When in doubt between a minimal fix and a fuller rewrite, propose the minimal one.
- If a paragraph is fine as-is, **say nothing**. Silence is a valid finding count of zero.

## House voice (preserve)

- Direct, second-person, terse. No hedging.
- Sentence fragments are intentional ("One pipeline. Two files only.") — keep them.
- Contractions (you'll, don't, it's) are intentional — keep them.
- Emojis already in the file (👋 🚀 ⚙ ✅) — preserve where they appear; do not add new ones.
- Avoid corporate-deck words: leverage, robust, seamless, powerful, cutting-edge, best-in-class.
- Avoid AI-slop tells: dive into, let's explore, in conclusion, it's worth noting that, in today's fast-paced …

## Fair game for edits

- Grammar and typos.
- Tightness — strike filler, redundant qualifiers, restated sentences.
- Voice drift — passages that read generic-LLM rather than workshop voice.
- Inconsistency — same concept named two different things across labs.
- Em-dash thinning — the guide is dash-heavy; some can become commas or periods without loss.

## Process

1. Read **$ARGUMENTS** end-to-end.
2. Walk the file **linearly, top to bottom**, skipping the off-limits regions above.
3. Build a **single batch report**. **Do not call the Edit or Write tool. Do not modify the file.**
4. Group findings by importance, in this order:

   **HIGH — clarity / correctness.** Prose that misleads, contradicts other labs, or reads ambiguously to a first-time attendee.

   **MEDIUM — tightness / voice.** Cuts and rewrites that meaningfully improve the guide. Filler removal, voice drift, awkward phrasing, repetition between labs.

   **LOW — polish.** Micro-edits: em-dash thinning, optional rephrases, small nits where the original is fine but a tighter form exists.

5. For each finding, emit exactly this shape:

   ```
   Line <N>  ·  <one-line summary>
     before:  <exact current text>
     after:   <proposed rewrite>
     why:     <one short clause — what the change buys>
   ```

6. End the report with a one-paragraph summary: total findings per tier, and the top 3 themes you saw across the document.

## What you must not do

- Do not call Edit, Write, or any other tool that modifies the file.
- Do not propose changes inside off-limits regions, even if they look wrong. If you must mention them, list them under a final `Skipped (off-limits)` note — never as findings.
- Do not invent style rules not listed here.
- Do not summarise what the lab guide is about. Go straight to findings.
