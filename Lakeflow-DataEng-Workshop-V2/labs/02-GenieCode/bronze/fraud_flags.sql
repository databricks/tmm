-- GENIE_CODE_GENERATED | 2026-05-17T13:34:00Z | Ingest fraud flag JSON files

CREATE OR REFRESH STREAMING TABLE fraud_flags
TBLPROPERTIES ('created_by' = 'genie_code', 'created_at' = '2026-05-17T13:34:00Z')
AS SELECT * FROM STREAM(read_files(
  '/Volumes/ops_data/shared/landing/booking_fraud_flags/',
  format => 'json'
));
