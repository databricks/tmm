# 🛵 Auto-Refund — The Omnigent Demo (run sheet)

**The whole demo is this file.** You drive the Omnigent **web UI** and narrate; the agents generate everything live. The mechanics below were verified end-to-end against a live Omnigent deployment on 2026-06-26.

**The setup (one breath):** You're a **PM on the Orders team at a food-delivery app**. You're scoping one feature — **Auto-Refund**: when an order fails (never delivered, cancelled before it arrives, or missing/wrong items), the customer is refunded automatically and immediately, instead of tapping "report a problem" and waiting days for a human. You'll (1) use two AI models from different labs to pressure-test it and draft a light PRD, (2) hit a question only the Payments team can answer and pull in a teammate on the live session, and (3) hand the build to agents that run in the cloud overnight.

**The arc:** more brains → more people → no laptop. **Meta wink (open or close):** *"The assistant that helped build this demo runs inside Omnigent. Everything you're about to see, it does to itself."*

- ⏱️ ~10–12 min · 👥 Customer-facing · 🧑‍🤝‍🧑 Teammate on standby for Act 2
- Legend: 🎤 = say · 🖱️ = click · ⌨️ = type · ✅ = verified live · ✳️ = illustrative / CLI alt

> **Pre-flight:** Logged into your workspace's Omnigent (`https://<your-databricks-workspace>/omnigent`). Context repo public & handy: **`https://github.com/Incognico-o/auto-refund-demo`**. Teammate ready to open a link. Optionally pre-run one session as a fallback (Act 1 takes ~3–5 min).

---

## Act 1 — Two models pressure-test the feature, then draft a light PRD
**Capability:** Omnigent's built-in **Debby** agent sends every prompt to a **Claude** model 🟠 *and* a **GPT** model 🔵 (different labs), compares them, and can have them debate. **Why a customer cares:** refunds move real money — one model's blind spot is a fraud hole or a double-refund incident. A builder + a skeptic catch more, on one governed bill.

🎤 *"I'm a PM on the Orders team. We want to ship Auto-Refund — if your order fails, you get your money back automatically, no 'report a problem,' no waiting. Refunds are easy to get subtly wrong, so before I write anything I'm going to have two models — one from Anthropic, one from OpenAI — stress-test it."*

**Set up the session (home screen):**
- 🖱️ Agent picker (defaults to "Claude Code") → **✅ Debby — Multi-agent debate**.
- 🖱️ Host button → **✅ Databricks Sandbox**. 🎤 *"This runs in a Databricks-managed serverless sandbox, not on my laptop — that matters in act three."*
- 🖱️ **Repository** → paste **`https://github.com/Incognico-o/auto-refund-demo`**, branch **`main`** (the button then reads `auto-refund-demo#main`). ✅ Omnigent clones it into the sandbox as the working directory, so the agent starts with our context — the app, the **Orders vs. Payments** boundary, the `order_failed` schema, and the draft contract. 🎤 *"I'm pre-loading my team's context as a repo, so I don't paste a wall of background — and the agents build into it later."*
- ⌨️ Now the opener is one line — start the session:
> Read the repo for context (README + docs/payments-contract.DRAFT.md), then have your two partners pressure-test our Auto-Refund feature and flag the open questions for the Payments team.
> ✅ **Verified:** Debby `ls`'d the repo, read the README/schema/contract ("I have full context now"), then dispatched the Claude 🟠 + GPT 🔵 partners. (Files panel shows "No files" until the clone finishes, then the tree appears.)
> 💬 **No repo? Fallback brief:** *"I'm a PM on the Orders team at our food-delivery app. We want to ship Auto-Refund: when an order fails — never delivered, cancelled, or missing/wrong items — refund the customer automatically instead of 'report a problem' + waiting. Pressure-test and scope it."*

> ✅ **What happens (verified live):** Debby fans your brief to a **Claude** head 🟠 and a **GPT** head 🔵, posts both independent takes + a **"where they agree / differ"** read, then offers next steps (a one-page PRD and/or a `/debate`). Narrate the two takes — your real "two labs, two blind spots" moment: in the dry run **Claude** flagged *demand-side* fraud (unfalsifiable "never delivered" claims, "who eats the loss," auto-refund + chargeback double-dip) while **GPT** brought the *supply-side* angle (couriers faking "delivered," GPS/photo spoofing, stacked-order abuse) + concrete fixes (a 5–10 min "soft-hold" window, handoff-proof tokens, a componentized idempotent ledger). Then ask for the light doc — **don't rely on the (a)/(b) labels, they vary run-to-run; just type what you want:**
> ⌨️ **Turn this into a light one-page PRD I can read on screen, under ~250 words: the problem, the 3 most important features, 1–2 success metrics, and end with "Open questions for the Payments team."**
> ✅ **Verified output:** a ~230-word PRD — **Problem · 3 Features · Success Metrics · Open Questions for the Payments team** — legible on one screen, and that last section *is* your Act 2 hook (it surfaced loss-ownership, refund instrument, chargeback dedup, and tip handling — all Payments calls).
> 🎁 **Want them to visibly argue (not just give parallel takes)?** Lead with `/debate … for 1 round` instead — same two models, but you watch them critique each other and converge before the PRD. More drama, ~2 min longer.

🎤 **Why two models (the proof point):** *"The skeptic forced the questions a single model glosses over — who eats it when someone fakes a 'never arrived,' how we avoid double-refunding, what counts as 'delivered.' The builder kept it focused on the customer-trust win. That tension is the value, and it's one session, one bill."*

**Governance (for a customer audience):**
- 🖱️ **Agent tools and policies** → 🎤 *"One session, two vendors, one live running cost — and I can attach a **Session Cost Budget** that hard-caps spend and auto-downgrades the model, **Deny PII in LLM requests** (this is customer payment data), or require approval on shell/file ops."* (Show the **Add policy** list.) *"Governed, audited, guardrails the agent can't talk its way around."*

---

## Act 2 — One question is Payments', not mine → pull in a teammate, live 📲
**Capability:** share the *live* session; a teammate joins and steers it. **Why a customer cares:** governed, real-time collaboration on the same running session — not screenshots in Slack.

🎤 *"Here's the honest part: my team owns **detecting** the failed order and deciding a refund is owed. But actually **moving the money** — refund vs. void, never double-refunding, partial refunds for missing items, owning the transaction record — that's the **Payments team**. Those open questions at the bottom of the PRD aren't mine to answer. So I'll bring in their PM on this exact session instead of starting a thread."*

**Share it (verified flow):**
- 🖱️ **Share session** → *"invite others to view or collaborate."*
- Flip **✅ "Any workspace user can view this session,"** or add the teammate by **User ID**, set **Level → ✅ Edit**, **Grant**.
- 🖱️ **Copy link** → Slack it. (It shows under her **"Shared with me."**)

🎤 *"Same live session, on her device, authenticated through our Databricks workspace, with the permission I set — Read to watch, Edit to drive."*

**Teammate drives (types into the shared session):**
> ⌨️ Payments PM here. Refunds touch the money path and the transaction record, which we own. Let's pin the contract: Orders emits an `order_failed` event (order id + failure reason); Payments decides void-vs-refund, guarantees idempotency so we never double-refund, handles partial refunds for missing items, and stays source of truth for the transaction. Add that to the PRD and note what each team owns.

🎤 *"That's the answer, written into the PRD by the team that owns it — live, in context. The cross-team gap is closed before a single line of code."*

---

## Act 3 — Hand the build to agents in the cloud, overnight 🌙🤖
**Capability:** the session already runs on a managed **Databricks Sandbox (Lakebox)** — so it keeps going with your laptop closed, and you reconnect from any device. **Why a customer cares:** no babysitting; isolated, serverless, governed.

🎤 *"We're aligned, the contract's in the PRD. Now the build. Remember the host is Databricks Sandbox — this has been running in the cloud the whole time, not on my machine."*

**Kick off the build:**
- 🖱️ **New session** → agent picker → **✅ Polly — Multi-agent coding** (or Claude Code) → host **✅ Databricks Sandbox** → attach the same **Repository** (`https://github.com/Incognico-o/auto-refund-demo`) so the build lands in `services/refunds/`.
- ⌨️ Hand over the build:
> Build the Auto-Refund MVP in `services/refunds/` per the repo's context and `docs/payments-contract.DRAFT.md`: consume `order_failed` (`schemas/order_failed.example.json`), implement an idempotent refund/void decision + a Payments client stub + the customer notification, and write tests. Commit as you go.

🎤 **(Close the laptop. Pause.)** *"Serverless compute, no credentials on the box, sandbox policies still enforced. Closing the lid."*

🎤 *"Tomorrow, from any device, I reopen the session URL:"*
- 🖱️ Reopen → **Files** tab (what it built) + **Shells** tab (what it ran). 🎤 *"It worked the PRD while I slept."* (Bonus: a long run is still shareable — Payments can watch progress too.)

> ✳️ **CLI alternative (automation/power-user audience):** `databricks sandbox create --name refund-build`, `databricks sandbox config <id> --no-autostop`, `databricks sandbox ssh <id> -- '…'`, `databricks sandbox status <id>`. Verified from CLI source, not clicked in this run.

---

## Close 🎬
🎤 *"More brains, more people, no laptop — a Claude and a GPT pressure-testing the feature into a tight PRD, the Payments PM closing the cross-team gap on the same live session, and agents finishing the build in the cloud overnight. And the assistant that helped me build this has been inside Omnigent the whole time. Same platform — swap the model, share the session, run it serverless — no rewrite."*

---

### Verified facts cheat-sheet (for stage Qs)
- **Agents in the picker:** Claude Code · Codex · Cursor · Pi · Polly (multi-agent coding) · Debby (multi-agent debate). ✅
- **Debby:** default = **side-by-side** (fans to a **Claude** 🟠 + **GPT** 🔵 sub-agent, shows both takes + "where they agree/differ," then offers debate-or-PRD); `/debate … for N rounds` adds visible cross-critique → synthesis; sub-agents show in the **Agents** panel. ✅
- **Host:** Databricks Sandbox (managed/serverless) or Connect new host; session shows "Provisioning sandbox…" then runs server-side. ✅
- **Repository attach:** paste a Git URL + branch on the launch screen → cloned into the sandbox as the working dir (public repos need no creds; private needs Databricks git credentials). Demo context repo: `github.com/Incognico-o/auto-refund-demo`. ✅
- **Share:** workspace-view toggle, or per-user **Read/Edit** grant + Copy link; you're **Owner**; teammate sees it under "Shared with me." ✅
- **Governance:** live **Session cost** + **Token usage**; **Add policy** incl. *Session Cost Budget* (hard-cap → forces model downgrade), *Per-User Daily Cost Budget*, *Deny PII in LLM Requests*, *Block Dangerous Shell Commands*, *Require Approval for File & Shell Ops*, *Deny Trivial Tasks on Expensive Models*, *Enforce Sandbox on Agent Start*, GitHub/Google/Gmail access controls. ✅

### Fallbacks
- **Debate/takes slow or long:** ask for "1 round" and keep the ~250-word cap; or fall back to a pre-run session — the PRD is the payoff, not the wait.
- **Teammate can't join:** flip the workspace-view toggle and screen-share, or read her message and narrate it.
- **Composer "Send" looks stuck after a paste:** edit one character in the box so the UI registers the text, then Send. (Typing normally + Enter sends fine.)
- **Don't rely on Debby's (a)/(b) labels** — they vary run-to-run; just type what you want ("turn this into a light one-page PRD…").
- **Act 1 timing:** the two model takes are the long pole (~3–5 min) — narrate them as they stream, or pre-open a pre-run session from the sidebar.
- **Files panel shows "No files" at first:** it populates once the host finishes cloning the repo / the agent starts — give it a few seconds.
- **"Sandbox launch failed" / "runner didn't come online":** transient managed-sandbox hiccup (hit it once on an Act 3 build). Retry, or start a fresh session for a new sandbox. Act 1 sessions provisioned fine — it's intermittent.
- **Polly skill chips can auto-prepend:** with Polly selected the composer shows `/cross-review`, `/fanout`, `/investigate`; focusing/clicking near them can prepend a skill to your message (we saw `/investigate` sneak in). Clear the box before typing the plain build prompt if you don't want a skill.
