-- Databricks notebook source
CREATE OR REPLACE STREAMING TABLE raw_space_events
(
  CONSTRAINT timestamp_not_null EXPECT (timestamp IS NOT NULL)
)
AS
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
          clientId="..."
          clientSecret="..." ;         
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
