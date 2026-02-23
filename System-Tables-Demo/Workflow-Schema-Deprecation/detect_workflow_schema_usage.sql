-- Script 1: Using system.access.table_lineage to find all assets referencing system.workflow.
-- You can run this in your workspace to identify notebooks, jobs, dashboards, pipelines, etc.
-- that reference the deprecated system.workflow schema.
-- See more: https://docs.databricks.com/aws/en/admin/system-tables/lineage#table-lineage-table

SELECT
    entity_type,
    entity_id,
    source_table_full_name,
    source_type,
    created_by,
    MAX(event_time) AS last_accessed,
    COUNT(*) AS reference_count,
    COLLECT_SET(source_table_name) AS workflow_tables_used
FROM system.access.table_lineage
WHERE source_table_catalog = 'system'
  AND source_table_schema = 'workflow'
  AND event_time >= CURRENT_DATE - INTERVAL 90 DAY
GROUP BY entity_type, entity_id, source_table_full_name, source_type, created_by
ORDER BY entity_type, last_accessed DESC;


-- Script 2: Using system.query.history to find queries still using the old schema.
-- You can run this to find the actual SQL queries that still reference system.workflow,
-- along with the associated dashboard, alert, notebook, job, or pipeline.
-- Note: Only queries running on SQL warehouses and serverless compute are tracked
-- in the system.query.history table.
-- See more: https://docs.databricks.com/aws/en/admin/system-tables/query-history#using-the-query-history-table

SELECT
    executed_by,
    statement_type,
    LEFT(statement_text, 500) AS query_preview,
    query_source.dashboard_id,
    query_source.alert_id,
    query_source.notebook_id,
    query_source.sql_query_id,
    query_source.job_info.job_id,
    query_source.pipeline_info.pipeline_id,
    compute.warehouse_id,
    execution_status,
    start_time
FROM system.query.history
WHERE LOWER(statement_text) LIKE '%system.workflow.%'
  AND start_time >= CURRENT_DATE - INTERVAL 90 DAY
ORDER BY start_time DESC;
