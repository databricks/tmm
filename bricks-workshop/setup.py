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

def install_dependencies():
    """
    This function is a no-op when running within a Databricks notebook 
    with %pip installed dependencies. If running externally, you may
    need to ensure that the 'databricks-vectorsearch' package is installed.
    """
    pass

def create_catalog_and_schema(spark, catalog: str, schema: str):
    """Create catalog and schema if they don't exist."""
    try:
        spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
        logger.info(f"Catalog {catalog} and schema {schema} ensured.")
    except Exception as e:
        logger.error(f"Failed to create catalog or schema: {e}")
        raise

def load_csv_to_table(spark, table: str, url: str, catalog: str, schema: str):
    """Download CSV, load into a Spark DataFrame, and save it as a Delta table."""
    try:
        logger.info(f"Loading CSV from {url} into table {catalog}.{schema}.{table}")
        resp = requests.get(url)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        spark_df = spark.createDataFrame(df)
        full_table = f"{catalog}.{schema}.{table}"
        spark_df.write.mode("overwrite").saveAsTable(full_table)
        logger.info(f"Successfully wrote table {full_table}")
    except Exception as e:
        logger.error(f"Error loading {table} from {url}: {e}")
        raise

def ensure_endpoint(client: VectorSearchClient, endpoint_name: str, timeout: int = 600, poll_interval: int = 10):
    """Ensure that a vector search endpoint exists and is ready."""
    try:
        endpoints = client.list_endpoints().get("endpoints", [])
        existing_names = [ep["name"] for ep in endpoints]
        if endpoint_name in existing_names:
            logger.info(f"Endpoint '{endpoint_name}' already exists.")
        else:
            logger.info(f"Creating endpoint '{endpoint_name}'")
            client.create_endpoint(name=endpoint_name, endpoint_type="STANDARD")
        
        # Wait for readiness
        start = time.time()
        while True:
            ep_info = client.get_endpoint(endpoint_name)
            state = ep_info.get("endpoint_status", {}).get("state", "UNKNOWN")
            logger.info(f"Endpoint status: {state}")
            if state in ("ONLINE", "PROVISIONED", "READY"):
                logger.info(f"Endpoint '{endpoint_name}' is ready.")
                break
            if state in ("FAILED", "OFFLINE"):
                raise RuntimeError(f"Endpoint '{endpoint_name}' failed with state '{state}'")
            if time.time() - start > timeout:
                raise TimeoutError(f"Timed out waiting for endpoint '{endpoint_name}' to be ready after {timeout} seconds")
            time.sleep(poll_interval)
    except Exception as e:
        logger.error(f"Error ensuring endpoint '{endpoint_name}': {e}")
        raise

def index_exists(client: VectorSearchClient, index_name: str) -> bool:
    """Check if a vector search index already exists (on any endpoint)."""
    try:
        # List all indexes and see if the name appears
        resp = client.list_indexes()
        for idx in resp.get("indexes", []):
            if idx.get("name") == index_name:
                return True
        return False
    except Exception as e:
        logger.warning(f"Could not list indexes (assuming none exist): {e}")
        return False

def create_delta_index(client: VectorSearchClient, endpoint_name: str, source_table: str,
                       index_name: str, pipeline_type: str,
                       primary_key: str, embedding_column: str):
    """Create a delta sync vector index, if not already present."""
    full_index_name = index_name
    if index_exists(client, full_index_name):
        logger.info(f"Index '{full_index_name}' already exists, skipping creation.")
        return
    try:
        logger.info(f"Creating index '{full_index_name}' on table '{source_table}' (pk={primary_key}, col={embedding_column})")
        client.create_delta_sync_index(
            endpoint_name=endpoint_name,
            source_table_name=source_table,
            index_name=full_index_name,
            pipeline_type=pipeline_type,
            primary_key=primary_key,
            embedding_source_column=embedding_column,
            embedding_model_endpoint_name="databricks-gte-large-en"
        )
        logger.info(f"Index '{full_index_name}' created.")
    except Exception as e:
        logger.error(f"Failed to create index '{full_index_name}': {e}")
        raise

def main(spark):
    # Configuration
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

    # Keys for indexing
    kb_pk = "kb_id"
    kb_text = "formatted_content"
    st_pk = "ticket_id"
    st_text = "formatted_content"

    # Step 1: Create catalog & schema
    create_catalog_and_schema(spark, catalog, schema)

    # Step 2: Load CSVs into Delta tables
    for tbl, url in csv_files.items():
        load_csv_to_table(spark, tbl, url, catalog, schema)

    # Step 3: Ensure vector search endpoint
    vs_client = VectorSearchClient()
    ensure_endpoint(vs_client, endpoint_name)

    # Step 4: Create vector search indexes
    kb_table = f"{catalog}.{schema}.knowledge_base"
    st_table = f"{catalog}.{schema}.support_tickets"

    create_delta_index(vs_client, endpoint_name, kb_table,
                       index_name=f"{catalog}.{schema}.knowledge_base_index",
                       pipeline_type="TRIGGERED",
                       primary_key=kb_pk, embedding_column=kb_text)

    create_delta_index(vs_client, endpoint_name, st_table,
                       index_name=f"{catalog}.{schema}.support_tickets_index",
                       pipeline_type="CONTINUOUS",
                       primary_key=st_pk, embedding_column=st_text)

    logger.info("All setup steps completed successfully.")

if __name__ == "__main__":
    # In Databricks, `spark` is pre-defined. If running externally, you'll need to
    # initialize a SparkSession and attach this script appropriately.
    try:
        main(spark)
    except NameError:
        logger.error("This script expects `spark` to be globally available (Databricks environment).")
        sys.exit(1)
    except Exception as exc:
        logger.error(f"Setup failed: {exc}")
        sys.exit(1)