-- Databricks notebook source
CREATE OR REFRESH STREAMING LIVE TABLE raw_circulars
AS
SELECT *
FROM cloud_files('/Volumes/demo_frank/nasa/unpack/archive.json/*.json', 'JSON', 
    map(
    'multiline', 'true',
    'cloudFiles.inferColumnTypes', 'true',
    'cloudFiles.schemaLocation', '/tmp/circualars'
    
  )
);


CREATE OR REFRESH MATERIALIZED VIEW proc_circulars 
(CONSTRAINT valid_body EXPECT (body IS NOT NULL ) ON VIOLATION DROP ROW)
AS
SELECT 
  circularId::BIGINT as id, 
  (createdOn/1000)::timestamp as created,
  CONCAT('\n subject: ',subject, '\n body: ',  body) as body, 
  CONCAT('\n from: ', email, '\n by: ', submitter) as submitter
FROM (live.raw_circulars);


