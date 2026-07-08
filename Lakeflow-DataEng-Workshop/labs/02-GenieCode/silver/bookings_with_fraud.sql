-- GENIE_CODE_GENERATED | 2026-05-17T13:34:00Z | Mark bookings with fraud flags

CREATE OR REFRESH MATERIALIZED VIEW bookings_with_fraud
TBLPROPERTIES ('created_by' = 'genie_code', 'created_at' = '2026-05-17T13:34:00Z')
AS
SELECT
  b.*,
  CASE WHEN f.flag = 'fraud' THEN true ELSE false END AS is_fraud,
  f.confidence AS fraud_confidence,
  f.reason AS fraud_reason
FROM bookings b
LEFT JOIN fraud_flags f ON b.booking_id = f.booking_id;
