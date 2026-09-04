# Writing-style / GEO review changelog

## 01-marketplace.md

### Style
- Rewrote the lede: replaced the em dash with a period + colon so the synthetic-vs-real contrast survives without an AI-tell dash.
- Dropped the "Specifically," filler connector and turned the em dash in the "You attach…" sentence into a comma; unbolded "read-only Unity Catalog catalog" to cut bold density.
- Fact-table "Resulting table" row: removed the em dash and the `…` ellipsis (both common AI tells); listed columns as "(longitude, latitude, velocity, and more)".
- IMPORTANT callout: split the em dash into two sentences ("Get the catalog name exactly right. Set it to `marketplace`.").
- Image alt text: replaced the em dash with a colon.

### Notes (not applied)
- Nav-table label "Genie Agents — EDA" and the "| — |" placeholder still contain em dashes. Left as-is because the label mirrors page 02's title; handle in a whole-tutorial pass to avoid cross-page drift.
- No code, commands, SQL, or paths were altered.

## 02-genie-eda.md

### Style
- Converted the fake step blockquote (bold "Step N" lines) into a real numbered list, matching page 01; kept the prompt code block and the Step 3/4 bullets verbatim.
- Fixed terminology drift: "Genie agent interface" → "Genie Code interface" in the step you open.
- De-fluffed the lede: "are a great way to do EDA" → "run your EDA for you".
- Recap grammar/wordiness: "ask Genie to create you a written report which could be persisted and then reused for creating a SDP ETL pipeline later" → "ask Genie for a written report, then save it and reuse it to build the SDP ETL pipeline in Step 4" (also fixes "a SDP" → "the SDP").
- Removed em dashes (author preference / de-AI): intro, optional-viz paragraph, hourly-pattern paragraph, recap, and three image alt strings — replaced with periods/colons. Numeric-range en dashes left intact.
- Collapsed stray double blank lines after the H1, the EDA-run heading, and the Results image.

### GEO
- Added an answer-first "The short version:" lead under the H1 so the title's "how" is answered in the first three sentences.
- The numbered-list conversion also improves crawler extractability and scannability.

### Notes (not applied)
- Optional "At a glance" key-facts block (for cross-page uniformity with page 01) was proposed but not added — flagged as opt-in and not confirmed.
- No code, commands, SQL, or paths were altered.
