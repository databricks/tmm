# Databricks notebook source
# MAGIC %load_ext autoreload
# MAGIC %autoreload 2
# MAGIC # Enables autoreload; learn more at https://docs.databricks.com/en/files/workspace-modules.html#autoreload-for-python-modules
# MAGIC # To disable autoreload; run %autoreload 0

# COMMAND ----------

# DBTITLE 1,Run Setup
# MAGIC %run ./Setup_00

# COMMAND ----------

# DBTITLE 1,Notebook title
# MAGIC %md
# MAGIC # Lakebase Search
# MAGIC Lakebase vector, text, and hybrid search over 10,000 real Amazon Electronics products (McAuley-Lab/Amazon-Reviews-2023).

# COMMAND ----------

# DBTITLE 1,Typical Search Bar for Applications
display(
    ProductSearchBarWidget(
        fetch_fn=fetch_pg_df,
        embed_fn=embed_fn,
        database_name=DATABASE_NAME,
        table_name=f"{PG_SCHEMA}.products",
        embedding_model=EMBEDDING_MODEL,
        query_text="",
    )
)

# COMMAND ----------

# DBTITLE 1,Agentic retrieval
# MAGIC %md
# MAGIC ## Agentic Retrieval
# MAGIC A support agent for the same storefront, with four retrieval tools over Lakebase: `search_memory` (past conversations with this customer), plus `vector_search_products`, `text_search_products` and `hybrid_search_products`. The agent decides which tools to call and how many times — every search is streamed into the UI as it happens.

# COMMAND ----------

# DBTITLE 1,Support Agents Searching over Memories and Products
display(
    SupportAgentWidget(
        chat_fn=chat_fn,
        fetch_fn=fetch_pg_df,
        embed_fn=embed_fn,
        database_name=DATABASE_NAME,
        products_table=f"{PG_SCHEMA}.products",
        memory_table=MEMORY_TABLE,
        embedding_model=EMBEDDING_MODEL,
        customer_name=CUSTOMER_NAME,
        model_label=LLM_ENDPOINT,
        max_steps=8,
    )
)

# COMMAND ----------

# DBTITLE 1,Agent Document Pipeline
# MAGIC %md
# MAGIC ## Agent Document Pipeline
# MAGIC
# MAGIC Documents that an agent works on iteratively — knowledge articles, playbooks, product guides — can be long enough to require **chunking** before embedding. This section uses a fully automated pipeline:
# MAGIC
# MAGIC 1. **Source of truth**: A Lakebase Postgres table (`agent_documents`) — the agent writes directly to Lakebase
# MAGIC 2. **Lakebase CDF**: Row-level changes are captured and written to a Delta history table (`lb_agent_documents_history`) in Unity Catalog
# MAGIC 3. **Lakeflow SDP pipeline**: APPLY CHANGES reconstructs current document state → Materialized View chunks and embeds each document via `ai_query` with 1024-dim vectors
# MAGIC 4. **Triggered job**: A table-update trigger on the CDF history table automatically runs the pipeline whenever a document is created or edited
# MAGIC 5. **Synced Table** (Snapshot mode): `synced_document_chunks` syncs the MV output back to Lakebase for hybrid search
# MAGIC

# COMMAND ----------

# DBTITLE 1,Agent Modifies Documents
# ── Helper functions for the Agent Document Widget ──────────────────────
# DOC_TABLE, DOC_ID, and AgentDocumentWidget class are provided by Setup_00
def spark_merge_fn(doc_id, title, content):
    """Upsert a document into the Lakebase source table (triggers CDF event)."""
    with connect_postgres() as _conn:
        with _conn.cursor() as _cur:
            _cur.execute(
                f"INSERT INTO {DOC_TABLE} (doc_id, title, content) "
                f"VALUES (%s, %s, %s) "
                f"ON CONFLICT (doc_id) DO UPDATE SET "
                f"title = EXCLUDED.title, content = EXCLUDED.content, updated_at = now()",
                (doc_id, title, content.strip()),
            )


def fetch_documents_fn():
    """Fetch all agent documents from Lakebase."""
    _df = fetch_pg_df(
        f"SELECT doc_id, title, content, updated_at FROM {DOC_TABLE} ORDER BY updated_at DESC",
        dbname=DATABASE_NAME,
    )
    result = []
    for _, row in _df.iterrows():
        dt_val = row["updated_at"]
        result.append({
            "doc_id":      row["doc_id"],
            "title":       row["title"] or "",
            "content":     row["content"] or "",
            "content_len": len(row["content"] or ""),
            "updated_at":  dt_val.strftime("%b %d %H:%M") if hasattr(dt_val, 'strftime') else str(dt_val)[:16],
        })
    return result


# ── Adapter: wrap chat_fn so it returns plain text (not a message dict) ──
def agent_chat_fn(messages):
    """Call the LLM and return just the text content."""
    msg = chat_fn(messages)
    return msg.get("content", "") if isinstance(msg, dict) else str(msg)


# ── Display the widget ──────────────────────────────────────────────────────────────
display(
    AgentDocumentWidget(
        chat_fn=agent_chat_fn,
        spark_merge_fn=spark_merge_fn,
        fetch_documents_fn=fetch_documents_fn,
        initial_doc_id=DOC_ID,
    )
)

# COMMAND ----------

# DBTITLE 1,Agent Searches over Documents
# DocumentSearchAgentWidget class is provided by Setup_00


def fetch_document_fn(doc_id):
    """Fetch a full document from the Lakebase source table."""
    _df = fetch_pg_df(
        f"SELECT doc_id, title, content FROM {DOC_TABLE} WHERE doc_id = %s",
        params=(doc_id,),
        dbname=DATABASE_NAME,
    )
    if _df.empty:
        return None
    _r = _df.iloc[0]
    return {"doc_id": _r["doc_id"], "title": _r["title"], "content": _r["content"]}


display(
    DocumentSearchAgentWidget(
        chat_fn=chat_fn,
        fetch_fn=fetch_pg_df,
        embed_fn=embed_fn,
        fetch_document_fn=fetch_document_fn,
        database_name=DATABASE_NAME,
        chunks_table=f"{PG_SCHEMA}.synced_document_chunks",
        embedding_model=EMBEDDING_MODEL,
        model_label=LLM_ENDPOINT,
    )
)