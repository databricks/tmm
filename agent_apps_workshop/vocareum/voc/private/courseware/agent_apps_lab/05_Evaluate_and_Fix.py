# Databricks notebook source
# MAGIC %md
# MAGIC # 📊 Module 5 — Evaluate & Fix your agent
# MAGIC ### Measure the planted bugs with LLM judges, fix the prompt, prove the gain
# MAGIC
# MAGIC In Module 4 your agent got the **AudioMax Pro warranty wrong** (*3 years* from a marketing
# MAGIC doc; the official policy is *1 year*). This notebook turns that gut-feel into a
# MAGIC **measurement**: eval set → **MLflow LLM judges** → baseline fails → **fix the prompt** →
# MAGIC re-run → score goes up.
# MAGIC
# MAGIC > **Ready to run top-to-bottom** (*Run all*). You only edit one thing — the instructions in
# MAGIC > the "fix" cell.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Install dependencies
# MAGIC `databricks-vectorsearch` is pinned to `0.73` deliberately (0.74 broke an import
# MAGIC `databricks-openai` needs). The kernel restarts after install — run cells in order.

# COMMAND ----------

# MAGIC %pip install -U "mlflow>=3.1" openai-agents databricks-openai databricks-sdk "databricks-vectorsearch==0.73" databricks-agents --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Build your agent in-process
# MAGIC Imports the **same `agent/app.py`** you deployed; tools still run **on-behalf-of-you**, so UC
# MAGIC governance applies exactly like the deployed app.

# COMMAND ----------

import asyncio
import os
import sys

import nest_asyncio
nest_asyncio.apply()  # the agent is async; this lets asyncio.run(...) work inside the notebook

# Import the shipped agent (app.py) from your agent/ folder.
_email = spark.sql("SELECT current_user() AS u").collect()[0]["u"]
_agent_dir = f"/Workspace/Users/{_email}/agent_apps_lab/agent"
if _agent_dir not in sys.path:
    sys.path.insert(0, _agent_dir)
import app  # noqa: E402  (sets up the FMAPI chat_completions client + defines the tools/agent)
from agents import Agent, Runner  # noqa: E402

import mlflow  # noqa: E402

# CRITICAL — keep this line, and keep it BEFORE any mlflow.genai.evaluate call. evaluate
# auto-enables openai autolog, which breaks the OpenAI-Agents-SDK-on-FMAPI path (mlflow #15692 /
# openai-agents #680) and kills the trace. Explicitly disabling makes evaluate skip re-enabling
# it; our manual @mlflow.trace below still gives the judges one clean, real trace per row.
mlflow.openai.autolog(disable=True)

# Point evaluation runs at your own experiment (genai.evaluate needs an active experiment).
mlflow.set_experiment(f"/Users/{_email}/techmart_agent_eval")

print(f"Agent ready. LLM = {app.LLM_ENDPOINT}; tools run OBO as {_email}")


def make_agent(instructions: str) -> Agent:
    """Build a TechMart agent with custom instructions, reusing app.py's OBO tools + model."""
    return Agent(
        name="TechMart Support",
        instructions=instructions,
        tools=[app.get_product_details, app.get_return_policy, app.get_order_status,
               app.search_products, app.whoami],
        model=app.LLM_ENDPOINT,
    )


def ask(agent: Agent, question: str) -> str:
    # An LLM round-trip can occasionally return an EMPTY final_output.
    # Retry; if still empty, return a visible marker so the judge fails the row loudly.
    for _ in range(3):
        out = asyncio.run(Runner.run(agent, question)).final_output
        if out and str(out).strip():
            return str(out)
    return "(the agent returned an empty response after 3 attempts)"


# Quick sanity check — this should surface the planted 3-year warranty bug at baseline:
_baseline_instructions = app.build_agent().instructions
print("\nSanity check (baseline):")
print(ask(make_agent(_baseline_instructions), "How long is the warranty on the AudioMax Pro?")[:300])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. The evaluation dataset
# MAGIC Five realistic support questions. Three target the **planted bugs** (warranty, availability,
# MAGIC over-permissive returns); two are neutral controls. Each row's `inputs` becomes the argument to
# MAGIC our predict function.

# COMMAND ----------

eval_dataset = [
    {"inputs": {"question": "How long is the warranty on the AudioMax Pro?"}},
    {"inputs": {"question": "Is the ProBook X500 available to buy right now?"}},
    {"inputs": {"question": "Can I return an opened laptop after 6 months just because I changed my mind?"}},
    {"inputs": {"question": "What's the status of order ORD-10001?"}},
    {"inputs": {"question": "Tell me about the ProBook X700."}},
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. LLM judges (MLflow `Guidelines` scorers)
# MAGIC Each judge reads question + answer and passes/fails a plain-English rule. **Guidelines are
# MAGIC conditional** ("if the question is about X…, else pass") so each judge only grades the rows
# MAGIC it's relevant to.

# COMMAND ----------

from mlflow.genai.scorers import Guidelines

scorers = [
    Guidelines(
        name="warranty_accuracy",
        guidelines=(
            "If the question asks about a product's WARRANTY length, the response must state the "
            "official policy term of ONE (1) year. If it cites 3 years (the marketing/product-doc "
            "figure) it FAILS. If the question is not about warranty, this guideline passes."
        ),
    ),
    Guidelines(
        name="availability_accuracy",
        guidelines=(
            "If the question asks whether a product is AVAILABLE to buy and that product is "
            "discontinued (e.g. the ProBook X500), the response must say it is NOT available / "
            "discontinued. If the question is not about availability, this guideline passes."
        ),
    ),
    Guidelines(
        name="policy_grounded",
        guidelines=(
            "If the question is about RETURNS or refunds, the response must reflect the official, "
            "limited return policy and must NOT promise unlimited, any-reason, or indefinite returns. "
            "If the question is not about returns, this guideline passes."
        ),
    ),
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Baseline evaluation
# MAGIC Run the **current** agent over the dataset and score it. Expect `warranty_accuracy` (and likely
# MAGIC `policy_grounded`) to fail — that's the bug we're about to fix. This takes ~1–2 minutes.

# COMMAND ----------

baseline_agent = make_agent(_baseline_instructions)


# @mlflow.trace produces a REAL trace per call (clean string in/out) — the judges score these.
# We rely on this manual trace and keep openai autolog DISABLED (see the build cell): autolog
# breaks the Agents-SDK-on-FMAPI path (mlflow #15692) and nulls the trace.
@mlflow.trace
def predict_baseline(question: str) -> str:
    return ask(baseline_agent, question)


baseline = mlflow.genai.evaluate(
    data=eval_dataset,
    predict_fn=predict_baseline,
    scorers=scorers,
)
print("BASELINE metrics:")
for k, v in sorted(baseline.metrics.items()):
    print(f"  {k}: {v}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. The fix — strengthen the instructions
# MAGIC A **prompt change**: the same minimal `instructions` string from `build_agent()`, now forcing
# MAGIC `get_return_policy` as the source of truth for warranty/returns over marketing text.
# MAGIC *(This is the one cell you edit — try your own wording and re-run!)*

# COMMAND ----------

fixed_instructions = (
    "You are TechMart's customer-support agent. Tools: get_product_details (price, category, "
    "availability), search_products (semantic product questions), get_return_policy (the SOURCE OF "
    "TRUTH for returns AND warranty terms), get_order_status (orders/PII).\n"
    "CRITICAL ACCURACY RULES:\n"
    "1. For ANY warranty or return question, you MUST call get_return_policy and use ONLY its terms. "
    "Call it with a POLICY CATEGORY as the topic — e.g. get_return_policy('warranty') or "
    "get_return_policy('return') — NOT a product name and NOT a whole sentence. If unsure, call "
    "get_return_policy('') to get all policies. NEVER quote a warranty length from "
    "get_product_details or product marketing text — those are often outdated.\n"
    "2. Treat the catalog's availability/status fields as authoritative: if a product is discontinued, "
    "it is NOT available, regardless of marketing copy.\n"
    "3. Never promise unlimited or any-reason returns; state the official policy's actual limits.\n"
    "Be concise and accurate."
)

fixed_agent = make_agent(fixed_instructions)


@mlflow.trace
def predict_fixed(question: str) -> str:
    return ask(fixed_agent, question)


fixed = mlflow.genai.evaluate(
    data=eval_dataset,
    predict_fn=predict_fixed,
    scorers=scorers,
)
print("FIXED metrics:")
for k, v in sorted(fixed.metrics.items()):
    print(f"  {k}: {v}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Compare baseline vs fixed
# MAGIC The aggregate tells the headline; the **per-row** table tells the story (which questions flipped
# MAGIC from ❌ to ✅). With only 5 rows, read the per-row results — one flaky call can move an average.

# COMMAND ----------

print("=" * 60)
print(f"{'metric':35s} {'baseline':>10s} {'fixed':>10s}")
print("=" * 60)
for k in sorted(baseline.metrics):
    if k.endswith("/mean") or "mean" in k:
        b = baseline.metrics.get(k)
        f = fixed.metrics.get(k)
        try:
            print(f"{k:35s} {b:>10.2f} {f:>10.2f}")
        except (TypeError, ValueError):
            print(f"{k:35s} {str(b):>10s} {str(f):>10s}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 🔎 Per-row detail
# MAGIC Open the **MLflow run** (the link printed by each `evaluate` call, or the Experiments icon on the
# MAGIC right rail) to see every question, your agent's answer, and each judge's pass/fail + rationale.
# MAGIC You should see the **warranty** row flip from ❌ (3 years) to ✅ (1 year) after the fix.

# COMMAND ----------

# Inline per-row view (baseline vs fixed) for the warranty/returns questions:
import pandas as pd  # noqa: E402

try:
    b_df = baseline.result_df if hasattr(baseline, "result_df") else baseline.tables.get("eval_results")
    f_df = fixed.result_df if hasattr(fixed, "result_df") else fixed.tables.get("eval_results")
    cols = [c for c in b_df.columns if "question" in c.lower() or "response" in c.lower()
            or "output" in c.lower() or "warranty" in c.lower() or "policy" in c.lower()]
    with pd.option_context("display.max_colwidth", 200):
        print("BASELINE:")
        print(b_df[cols].to_string() if cols else b_df.to_string())
        print("\nFIXED:")
        print(f_df[cols].to_string() if cols else f_df.to_string())
except Exception as e:  # noqa: BLE001
    print(f"(Open the MLflow run UI for the per-row table — inline view unavailable: {e})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ What you proved
# MAGIC You **measured** agent quality with reusable LLM judges, saw the **baseline fail** the
# MAGIC planted warranty bug, and **fixed it with a prompt change you can prove** with numbers.
# MAGIC
# MAGIC **Ship the fix:** ask Genie Code *"update the agent instructions to the fixed version and
# MAGIC redeploy"* — your app now answers **1 year**.
# MAGIC
# MAGIC **Bonus discussion:** the over-permissive returns doc may *not* fully fix with a prompt —
# MAGIC it's a **data** bug. Some problems are prompt bugs; others are data/governance bugs.
# MAGIC
# MAGIC **Next — Module 5½:** your deployed app has been writing every chat to **Lakebase** (in the
# MAGIC schema `00_Start_Here` printed). **Compute → Lakebase → Open Lakebase** → project "Agent Apps
# MAGIC Workshop Memory" → **SQL Editor** → query `<your schema>.agent_messages`.
