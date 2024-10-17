-- create flagship description for location 

USE catalog bakehouse_active;
USE SCHEMA pipelines;

DROP FUNCTION IF EXISTS gen_flagship_description;
CREATE FUNCTION gen_flagship_description(district STRING, city STRING, country STRING, ingredient STRING) RETURNS STRING
  RETURN ai_query(

    -- specify Databricks FM model 
    -- for LLama3: 'databricks-meta-llama-3-70b-instruct',
    'databricks-dbrx-instruct',

    -- LLM query to generate
    CONCAT('provide a 3 sentence description without saying "here is a 3 sentence description" \
    of a cookie bakehous flagship \
    store at the following trendy location:\n', district, " ", city," ", country,
    "which is mostly using the local ingredient ",ingredient)

  );


-- create table for dashboard


DROP TABLE IF EXISTS flagship_stores;
CREATE TABLE flagship_stores AS SELECT * FROM top_5;
ALTER TABLE flagship_stores ADD COLUMNS (description string);

UPDATE flagship_stores 
  -- apply LMM function
  SET description = gen_flagship_description(district, city , country, ingredient );



-- test it like this:
-- SELECT gen_flagship_description('Bondi Beach', "Sydney", "Australia", "oatmeal");

