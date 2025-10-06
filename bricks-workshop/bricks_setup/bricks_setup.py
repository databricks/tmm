# Databricks notebook source
# MAGIC %pip install --quiet databricks-vectorsearch
# MAGIC %restart_python
#!/usr/bin/env python3
import sys
import time
import logging
import requests
import pandas as pd
import io

from databricks.sdk import WorkspaceClient
from databricks.vector_search.client import VectorSearchClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def create_catalog_and_schema(spark, catalog: str, schema: str):
    try:
        spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
        logger.info(f"Ensured catalog `{catalog}` and schema `{schema}`.")
    except Exception as e:
        logger.error(f"Error creating catalog/schema: {e}")
        raise

def load_csv_to_table(spark, table: str, url: str, catalog: str, schema: str):
    try:
        logger.info(f"Loading table `{table}` from {url}")
        resp = requests.get(url)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        spark_df = spark.createDataFrame(df)
        full_table = f"{catalog}.{schema}.{table}"
        spark_df.write.mode("overwrite").saveAsTable(full_table)
        logger.info(f"Created table {full_table}")
    except Exception as e:
        logger.error(f"Error loading CSV for table {table}: {e}")
        raise

def enable_cdf(spark, catalog: str, schema: str, table: str):
    """Enable Delta change data feed (CDF) on the table."""
    full_name = f"{catalog}.{schema}.{table}"
    try:
        logger.info(f"Enabling CDF on {full_name}")
        spark.sql(f"""
            ALTER TABLE {full_name}
            SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
        """)
        logger.info(f"CDF enabled on {full_name}")
    except Exception as e:
        logger.warning(f"Could not enable CDF on {full_name}: {e}")
        # We don’t necessarily stop — maybe it's already enabled or unsupported.

def ensure_endpoint(client: VectorSearchClient, endpoint_name: str,
                    timeout: int = 600, poll_interval: int = 10):
    try:
        eps = client.list_endpoints().get("endpoints", [])
        names = [ep["name"] for ep in eps]
        if endpoint_name not in names:
            logger.info(f"Creating vector search endpoint '{endpoint_name}'")
            client.create_endpoint(name=endpoint_name, endpoint_type="STANDARD")
        else:
            logger.info(f"Endpoint '{endpoint_name}' already exists")

        start = time.time()
        while True:
            ep_info = client.get_endpoint(endpoint_name)
            state = ep_info.get("endpoint_status", {}).get("state", "UNKNOWN")
            logger.info(f"Endpoint state: {state}")
            if state in ("ONLINE", "PROVISIONED", "READY"):
                logger.info(f"Endpoint '{endpoint_name}' ready")
                break
            if state in ("FAILED", "OFFLINE"):
                raise RuntimeError(f"Endpoint '{endpoint_name}' failed (state={state})")
            if time.time() - start > timeout:
                raise TimeoutError(f"Timed out waiting for endpoint '{endpoint_name}' to be ready")
            time.sleep(poll_interval)
    except Exception as e:
        logger.error(f"Error ensuring endpoint: {e}")
        raise

def index_exists(client: VectorSearchClient, endpoint_name: str, index_name: str) -> bool:
    try:
        resp = client.list_indexes(name=endpoint_name)
        for idx in resp.get("indexes", []):
            if idx.get("name") == index_name:
                return True
        return False
    except Exception as e:
        logger.warning(f"Could not list indexes (assuming none exist): {e}")
        return False

def create_delta_index(client: VectorSearchClient, endpoint_name: str,
                       source_table: str, index_name: str,
                       pipeline_type: str, primary_key: str, embedding_column: str):
    if index_exists(client, endpoint_name, index_name):
        logger.info(f"Index '{index_name}' already exists — skipping")
        return

    try:
        logger.info(f"Creating index '{index_name}' on {source_table}")
        client.create_delta_sync_index(
            endpoint_name=endpoint_name,
            index_name=index_name,
            source_table_name=source_table,
            pipeline_type=pipeline_type,
            primary_key=primary_key,
            embedding_source_column=embedding_column,
            embedding_model_endpoint_name="databricks-gte-large-en"
        )
        logger.info(f"Index '{index_name}' created successfully")
    except Exception as ex:
        msg = str(ex)
        # Detect “no change data feed” error
        if "does not have change data feed enabled" in msg:
            logger.info(f"Detected missing CDF error for {source_table}. Trying to enable CDF and retry.")
            # Parse catalog.schema.table
            parts = source_table.split(".")
            if len(parts) == 3:
                cat, sch, tbl = parts
                try:
                    enable_cdf(spark, cat, sch, tbl)
                    logger.info(f"Retrying index creation '{index_name}' after enabling CDF")
                    client.create_delta_sync_index(
                        endpoint_name=endpoint_name,
                        index_name=index_name,
                        source_table_name=source_table,
                        pipeline_type=pipeline_type,
                        primary_key=primary_key,
                        embedding_source_column=embedding_column,
                        embedding_model_endpoint_name="databricks-gte-large-en"
                    )
                    logger.info(f"Index '{index_name}' created after retry")
                    return
                except Exception as e2:
                    logger.error(f"Retry failed for index '{index_name}': {e2}")
            else:
                logger.error(f"Could not parse table name '{source_table}' to enable CDF retry")
        logger.error(f"Failed to create index '{index_name}': {msg}")
        raise

def main(spark):
    catalog = "bricks_lab"
    schema = "default"
    endpoint_name = "bricks_endpoint"
    base_url = "https://raw.githubusercontent.com/databricks/tmm/main/bricks-workshop/data"
    csv_files = {
        "billing": f"{base_url}/billing.csv",
        "customers": f"{base_url}/customers.csv",
        "knowledge_base": f"{base_url}/knowledge_base.csv",
        "support_tickets": f"{base_url}/support_tickets.csv"
    }

    # Your specified keys
    kb_pk = "kb_id"
    kb_text = "formatted_content"
    st_pk = "ticket_id"
    st_text = "formatted_content"

    # Create catalog and schema
    create_catalog_and_schema(spark, catalog, schema)

    # Load tables
    for tbl, url in csv_files.items():
        load_csv_to_table(spark, tbl, url, catalog, schema)

    # Ensure vector search endpoint
    vs_client = VectorSearchClient()
    ensure_endpoint(vs_client, endpoint_name)

    # Enable CDF on source tables
    try:
        enable_cdf(spark, catalog, schema, "knowledge_base")
        enable_cdf(spark, catalog, schema, "support_tickets")
    except Exception as e:
        logger.warning(f"Failed enabling CDF for one or more tables: {e}")

    # Create indexes
    kb_full = f"{catalog}.{schema}.knowledge_base"
    st_full = f"{catalog}.{schema}.support_tickets"
    idx_kb = f"{catalog}.{schema}.knowledge_base_index"
    idx_st = f"{catalog}.{schema}.support_tickets_index"

    create_delta_index(vs_client, endpoint_name, kb_full, idx_kb, "TRIGGERED", kb_pk, kb_text)
    create_delta_index(vs_client, endpoint_name, st_full, idx_st, "TRIGGERED", st_pk, st_text)

    logger.info("Setup complete.")

if __name__ == "__main__":
    try:
        main(spark)
    except NameError:
        logger.error("This script must run in Databricks environment where `spark` is defined.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Setup script failed: {e}")
        sys.exit(1)