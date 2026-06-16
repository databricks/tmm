# Databricks notebook source
# MAGIC %md
# MAGIC # Module 1 · Explore the TechMart Data (≈10 min)
# MAGIC
# MAGIC In Module 2 you'll deploy an agent that answers **from this data** — tables through governed
# MAGIC SQL tools, marketing docs through Vector Search. Your agent will read *everything* you're
# MAGIC about to read. So: **does this data deserve your agent's trust?** Run the cells and jot down
# MAGIC anything that looks *off* — your hunches become test cases in Module 4 and measurements in
# MAGIC Module 5.
# MAGIC
# MAGIC > First query takes ~25s while the serverless warehouse warms up.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- THE CATALOG — the structured source of truth for products.
# MAGIC -- Read the `availability` and `warranty_years` columns closely... then read the marketing
# MAGIC -- `description` next to them. Do the columns and the prose always agree?
# MAGIC SELECT * FROM agent_apps_workshop.shared.products ORDER BY product_name LIMIT 50;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- CUSTOMER ORDERS — note what you can and CAN'T see. Customer PII (email, shipping address)
# MAGIC -- is governed by a Unity Catalog column mask: as a (non-admin) lab user you see ***REDACTED***.
# MAGIC -- Remember this view — in Module 3 the SAME mask fires through your deployed agent, because
# MAGIC -- the agent's data tools run on-behalf-of-YOU.
# MAGIC SELECT * FROM agent_apps_workshop.shared.orders LIMIT 20;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- THE OFFICIAL POLICIES — what TechMart actually promises (returns, warranty terms).
# MAGIC -- When a customer asks "how long is my warranty?", THIS is the answer a good agent gives.
# MAGIC -- Keep the warranty row in mind for the next cell.
# MAGIC SELECT * FROM agent_apps_workshop.shared.policies;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- THE MARKETING DOCS — written to SELL, not to be precise. These are also indexed in the
# MAGIC -- `product_docs_vs` Vector Search index, which means your agent will retrieve and read them
# MAGIC -- verbatim. Compare their claims against the catalog and policies you just saw:
# MAGIC -- do availability and warranty statements line up everywhere?
# MAGIC SELECT * FROM agent_apps_workshop.shared.product_docs LIMIT 20;

# COMMAND ----------

# MAGIC %md
# MAGIC ### Found anything? (don't fix it — *notice* it)
# MAGIC Read closely and at least one **Discontinued** product is still being sold by its doc, and a
# MAGIC **warranty** claim in the prose doesn't match the official policy. (A third, subtler one
# MAGIC hides in `policies` itself — extra credit.)
# MAGIC
# MAGIC This is the condition most agents ship into: structured data sound, prose enthusiastic. Your
# MAGIC agent reads both — **which will it believe?** Module 4: watch it pick a side. Module 5:
# MAGIC measure it, fix it, prove it.
# MAGIC
# MAGIC Next: open **Genie Code**, attach `LAB_CONTEXT.md`, and start **Module 2**.
