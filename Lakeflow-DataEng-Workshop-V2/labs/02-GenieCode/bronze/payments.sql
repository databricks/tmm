-- GENIE_CODE_GENERATED | 2026-05-17T13:34:00Z | Stream payments data

CREATE OR REFRESH STREAMING TABLE payments
TBLPROPERTIES ('created_by' = 'genie_code', 'created_at' = '2026-05-17T13:34:00Z')
AS SELECT * FROM STREAM(samples.wanderbricks.payments);
