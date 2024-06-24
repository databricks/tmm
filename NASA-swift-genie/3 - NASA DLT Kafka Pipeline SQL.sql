-- Databricks notebook source
CREATE OR REPLACE STREAMING TABLE raw_space_events AS
  SELECT offset, timestamp, value::string as msg
   FROM STREAM read_kafka(
    bootstrapServers => 'kafka.gcn.nasa.gov:9092',
    subscribe => 'gcn.classic.text.SWIFT_POINTDIR',
    startingOffsets => 'earliest',

    -- params kafka.sasl.oauthbearer.client.id
    `kafka.sasl.mechanism` => 'OAUTHBEARER',
    `kafka.security.protocol` => 'SASL_SSL',
    `kafka.sasl.oauthbearer.token.endpoint.url` => 'https://auth.gcn.nasa.gov/oauth2/token', 
    `kafka.sasl.login.callback.handler.class` => 'kafkashaded.org.apache.kafka.common.security.oauthbearer.secured.OAuthBearerLoginCallbackHandler',


    `kafka.sasl.jaas.config` =>  
         '
          kafkashaded.org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required
          clientId="7u2rpivvxxxxxxxxxxxxxxxxxxx"
          clientSecret="1errfm2jdgl0uolkb78kjnf8v94eyyyyyyyyyyyyyyy" ;         
         '
  );

-- COMMAND ----------

CREATE OR REPLACE MATERIALIZED VIEW split_events
COMMENT "Split Swift event message into individual rows"
AS
  WITH extracted_key_values AS (
    SELECT
      timestamp,
      split_part(line, ':', 1) AS key,
      TRIM(SUBSTRING(line, INSTR(line, ':') + 1)) AS value
    FROM (
      SELECT
        timestamp,
        explode(split(msg, '\\n')) AS line 
      FROM (LIVE.raw_space_events)
    )
    WHERE line != ''
  ),
  pivot_table AS (
    SELECT *
    FROM (
      SELECT key, value, timestamp
      FROM extracted_key_values
    )
    PIVOT (
      MAX(value) FOR key IN ('TITLE', 'NOTICE_DATE', 'NOTICE_TYPE', 'NEXT_POINT_RA', 'NEXT_POINT_DEC', 'NEXT_POINT_ROLL', 'SLEW_TIME', 'SLEW_DATE', 'OBS_TIME', 'TGT_NAME', 'TGT_NUM', 'MERIT', 'INST_MODES', 'SUN_POSTN', 'SUN_DIST', 'MOON_POSTN', 'MOON_DIST', 'MOON_ILLUM', 'GAL_COORDS', 'ECL_COORDS', 'COMMENTS')
    )
  )
  SELECT timestamp, TITLE, CAST(NOTICE_DATE AS TIMESTAMP) AS NOTICE_DATE, NOTICE_TYPE, NEXT_POINT_RA, NEXT_POINT_DEC, NEXT_POINT_ROLL, SLEW_TIME, SLEW_DATE, OBS_TIME, TGT_NAME, TGT_NUM, CAST(MERIT AS DECIMAL) AS MERIT, INST_MODES, SUN_POSTN, SUN_DIST, MOON_POSTN, MOON_DIST, MOON_ILLUM, GAL_COORDS, ECL_COORDS, COMMENTS
  FROM pivot_table

-- COMMAND ----------

CREATE OR REPLACE STREAMING TABLE split_events_st
COMMENT "Split Swift event message into individual rows"
AS
  WITH extracted_key_values AS (
    SELECT
      timestamp,
      split_part(line, ':', 1) AS key,
      TRIM(SUBSTRING(line, INSTR(line, ':') + 1)) AS value
    FROM (
      SELECT
        timestamp,
        explode(split(msg, '\\n')) AS line 
      FROM STREAM(LIVE.raw_space_events)
    )
    WHERE line != ''
  ),
  pivot_table AS (
    SELECT *
    FROM (
      SELECT key, value, timestamp
      FROM extracted_key_values
    )
    PIVOT (
      MAX(value) FOR key IN ('TITLE', 'NOTICE_DATE', 'NOTICE_TYPE', 'NEXT_POINT_RA', 'NEXT_POINT_DEC', 'NEXT_POINT_ROLL', 'SLEW_TIME', 'SLEW_DATE', 'OBS_TIME', 'TGT_NAME', 'TGT_NUM', 'MERIT', 'INST_MODES', 'SUN_POSTN', 'SUN_DIST', 'MOON_POSTN', 'MOON_DIST', 'MOON_ILLUM', 'GAL_COORDS', 'ECL_COORDS', 'COMMENTS')
    )
  )
  SELECT timestamp, TITLE, CAST(NOTICE_DATE AS TIMESTAMP) AS NOTICE_DATE, NOTICE_TYPE, NEXT_POINT_RA, NEXT_POINT_DEC, NEXT_POINT_ROLL, SLEW_TIME, SLEW_DATE, OBS_TIME, TGT_NAME, TGT_NUM, CAST(MERIT AS DECIMAL) AS MERIT, INST_MODES, SUN_POSTN, SUN_DIST, MOON_POSTN, MOON_DIST, MOON_ILLUM, GAL_COORDS, ECL_COORDS, COMMENTS
  FROM pivot_table

-- COMMAND ----------



/*
example message:
TITLE:           GCN/SWIFT NOTICE
NOTICE_DATE:     Thu 11 Apr 24 21:12:43 UT
NOTICE_TYPE:     SWIFT Pointing Direction
NEXT_POINT_RA:    48.356d {+03h 13m 25s} (J2000)
NEXT_POINT_DEC:  -30.147d {-30d 08' 49"} (J2000)
NEXT_POINT_ROLL: 310.400d
SLEW_TIME:       76380.00 SOD {21:13:00.00} UT
SLEW_DATE:       20411 TJD;   102 DOY;   24/04/11
OBS_TIME:        1080.00 [sec]   (=18.0 [min])
TGT_NAME:        TRANSIENT_10 
TGT_NUM:         97530,   Seg_Num: 4
MERIT:           69.00
INST_MODES:      BAT=0=0x0  XRT=7=0x7  UVOT=12485=0x30C5
SUN_POSTN:        20.78d {+01h 23m 07s}   +8.74d {+08d 44 34"}
SUN_DIST:         47.12 [deg]   Sun_angle= -1.8 [hr] (East of Sun)
MOON_POSTN:       62.23d {+04h 08m 56s}  +25.03d {+25d 01 48"}
MOON_DIST:        56.62 [deg]
MOON_ILLUM:      13 [%]
GAL_COORDS:      227.01,-58.82 [deg] galactic lon,lat of the pointing direction
ECL_COORDS:       34.38,-45.88 [deg] ecliptic lon,lat of the pointing direction
COMMENTS:        SWIFT Slew Notice to a preplanned target.  
COMMENTS:        Note that preplanned targets are overridden by any new BAT Automated Target.  
COMMENTS:        Note that preplanned targets are overridden by any TOO Target if the TOO has a higher Merit Value.  
COMMENTS:        The spacecraft longitude,latitude at Notice_time is 203.45,18.92 [deg].  
COMMENTS:        This Notice was ground-generated -- not flight-generated.  
*/

-- COMMAND ----------

/**

-- Create or refresh the streaming live table named "swift_split"
CREATE OR REFRESH STREAMING LIVE TABLE swift_split
-- Add a comment to describe the purpose of the table
COMMENT "Split Swift event message into individual rows"
AS
-- Begin the main SELECT statement
SELECT
  -- Select the timestamp column
  timestamp,
  -- Use MAX and CASE statements to extract the value for each key and assign it to a column
  MAX(CASE WHEN key = 'TITLE' THEN value ELSE NULL END) AS TITLE,
  MAX(CASE WHEN key = 'NOTICE_DATE' THEN value ELSE NULL END) AS NOTICE_DATE,
  MAX(CASE WHEN key = 'NOTICE_TYPE' THEN value ELSE NULL END) AS NOTICE_TYPE,
  MAX(CASE WHEN key = 'NEXT_POINT_RA' THEN value ELSE NULL END) AS NEXT_POINT_RA,
  MAX(CASE WHEN key = 'NEXT_POINT_DEC' THEN value ELSE NULL END) AS NEXT_POINT_DEC,
  MAX(CASE WHEN key = 'NEXT_POINT_ROLL' THEN value ELSE NULL END) AS NEXT_POINT_ROLL,
  MAX(CASE WHEN key = 'SLEW_TIME' THEN value ELSE NULL END) AS SLEW_TIME,
  MAX(CASE WHEN key = 'SLEW_DATE' THEN value ELSE NULL END) AS SLEW_DATE,
  MAX(CASE WHEN key = 'OBS_TIME' THEN value ELSE NULL END) AS OBS_TIME,
  MAX(CASE WHEN key = 'TGT_NAME' THEN value ELSE NULL END) AS TGT_NAME,
  MAX(CASE WHEN key = 'TGT_NUM' THEN value ELSE NULL END) AS TGT_NUM,
  MAX(CASE WHEN key = 'MERIT' THEN value ELSE NULL END) AS MERIT,
  MAX(CASE WHEN key = 'INST_MODES' THEN value ELSE NULL END) AS INST_MODES,
  MAX(CASE WHEN key = 'SUN_POSTN' THEN value ELSE NULL END) AS SUN_POSTN,
  MAX(CASE WHEN key = 'SUN_DIST' THEN value ELSE NULL END) AS SUN_DIST,
  MAX(CASE WHEN key = 'MOON_POSTN' THEN value ELSE NULL END) AS MOON_POSTN,
  MAX(CASE WHEN key = 'MOON_DIST' THEN value ELSE NULL END) AS MOON_DIST,
  MAX(CASE WHEN key = 'MOON_ILLUM' THEN value ELSE NULL END) AS MOON_ILLUM,
  MAX(CASE WHEN key = 'GAL_COORDS' THEN value ELSE NULL END) AS GAL_COORDS,
  MAX(CASE WHEN key = 'ECL_COORDS' THEN value ELSE NULL END) AS ECL_COORDS,
  MAX(CASE WHEN key = 'COMMENTS' THEN value ELSE NULL END) AS COMMENTS
-- Begin a subquery to extract key-value pairs from the input message
FROM (
  SELECT
    timestamp,
    -- Split each line by the first occurrence of ':' and assign the parts to 'key' and 'value' columns
    split_part(line, ':', 1) AS key,
    TRIM(SUBSTRING(line, INSTR(line, ':') + 1)) AS value
  FROM (
    SELECT
      timestamp,
      -- Explode the 'msg' column by splitting it on newline characters
      explode(split(msg, '\\n')) AS line
    FROM STREAM(LIVE.raw_space_events)
  )
  -- Filter out empty lines
  WHERE line != ''
)
-- Group the result by timestamp to aggregate the key-value pairs for each event
GROUP BY timestamp;

**/
