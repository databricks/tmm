
USE CATALOG {{my_catalog}} ;
USE SCHEMA {{my_schema}} ;


CREATE OR REPLACE TABLE flagship_stores AS
SELECT
  *,  -- Selects all original columns from the source table
  ai_translate(description, 'es') AS desc_es,
  ai_analyze_sentiment(description) AS sentiment
FROM
  flagship_stores;