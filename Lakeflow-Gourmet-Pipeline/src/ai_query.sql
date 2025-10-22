-- use params from DAB
USE CATALOG {{my_catalog}} ;
USE IDENTIFIER({{my_schema}});

DROP FUNCTION IF EXISTS gen_marketing_campaign;


-- FUNCTION: gen_marketing_campaign
-- Description: Generates culturally, calorie and context-aware marketing campaigns using AI

CREATE FUNCTION gen_marketing_campaign(
    district STRING COMMENT  'district/neighborhood name like Bondi Beach, Mission District', 
    city STRING COMMENT'City name where the store is located like Sydney, New York', 
    country STRING COMMENT'country name like USA or Australia', 
    ingredient STRING COMMENT 'Local ingredient to feature like macadamia nuts, matcha'
) RETURNS STRING

COMMENT 
    'Generates culturally, calorie and context-aware marketing campaigns for gourmet pipeline food company using AI.

    Returns: 3-sentence marketing description formatted as:
    1. How the cookie captures local essence and environment
    2. Why locals would enjoy this recipe based on lifestyle  
    3. Calorie classification presented positively for local lifestyle

    Agent Usage: Call this function to create personalized marketing content that resonates 
    with local culture and includes calorie-matched snacks for target demographics.

    AI Model: Uses databricks-claude-3-7-sonnet for natural language generation.'

RETURN 
  ai_query(
    'databricks-claude-3-7-sonnet',
    'Create a seasonal cookie recipe description for the district ' || district || 
    ' in the city ' || city || ' in country ' || country || 
    ' using the local ingredient ' || ingredient || 
    '. Format: First sentence - Describe how the cookie captures the essence of the location and connects to the local environment. ' ||
    'Second sentence - Explain why local people (like surfers, city workers, etc.) would enjoy this recipe based on their lifestyle. ' ||
    'Third sentence - Classify the calorie level (low, medium, or high) in a positive, appealing way that relates to the local lifestyle. ' ||
    'Keep it captivating and make sure each sentence flows naturally while highlighting the connection between the cookie, location, and local culture.'
    );

-- create gold table for dashboard with AI-generated descriptions in one step
DROP TABLE IF EXISTS flagship_stores;

CREATE TABLE flagship_stores AS 
SELECT 
    *,
    gen_marketing_campaign(
        district, 
        city, 
        country, 
        ingredient
    ) AS description
FROM 
    top_5;

-- you can test the function like this:
-- SELECT gen_flagship_description('Bondi Beach', 'Sydney', 'Australia', 'oatmeal');