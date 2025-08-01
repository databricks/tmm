
USE CATALOG demos1;
USE SCHEMA `gourmet-snacks`;

--ALTER TABLE flagship_stores
--ADD COLUMN desc_es STRING;

-- ALTER TABLE flagship_stores
--ADD COLUMN sentiment STRING;


CREATE OR REPLACE TABLE flagship_stores AS
SELECT
  *,  -- Selects all original columns from the source table
  ai_translate(description, 'es') AS desc_es,
  ai_analyze_sentiment(description) AS sentiment
FROM
  flagship_stores;