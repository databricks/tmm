-- create flagship description for location 

-- USE CATALOG :target_catalog;
-- USE SCHEMA :target_schema;
USE CATALOG demos1;
USE SCHEMA `gourmet-snacks`;

DROP FUNCTION IF EXISTS gen_flagship_description;

CREATE FUNCTION gen_flagship_description(
    district STRING, 
    city STRING, 
    country STRING, 
    ingredient STRING
) RETURNS STRING
  RETURN ai_query(
    'databricks-claude-sonnet-4',
    CONCAT(
        'Create a seasonal cookie recipe description for the district ', 
        district, ' in the city ', city, ' in country ', country, 
        ' using the local ingredient ', ingredient, 
        '. Format: First sentence - Describe how the cookie captures the essence of the location and connects to the local environment. ',
        'Second sentence - Explain why local people (like surfers, city workers, etc.) would enjoy this recipe based on their lifestyle. ',
        'Third sentence - Classify the calorie level (low, medium, or high) in a positive, appealing way that relates to the local lifestyle. ',
        'Keep it captivating and make sure each sentence flows naturally while highlighting the connection between the cookie, location, and local culture.'
    )
);

-- create gold table for dashboard with AI-generated descriptions in one step
DROP TABLE IF EXISTS flagship_stores;

CREATE TABLE flagship_stores AS 
SELECT 
    *,
    gen_flagship_description(
        district, 
        city, 
        country, 
        ingredient
    ) AS description
FROM 
    top_5;

-- you can test the function like this:
-- SELECT gen_flagship_description('Bondi Beach', 'Sydney', 'Australia', 'oatmeal');