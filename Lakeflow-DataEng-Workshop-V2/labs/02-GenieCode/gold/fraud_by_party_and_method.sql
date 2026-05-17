-- GENIE_CODE_GENERATED | 2026-05-17T13:34:00Z | Fraud risk by party size and payment method

CREATE OR REFRESH MATERIALIZED VIEW fraud_by_party_and_method
TBLPROPERTIES ('created_by' = 'genie_code', 'created_at' = '2026-05-17T13:34:00Z')
AS
SELECT
  bwf.guests_count AS party_size,
  p.payment_method,
  COUNT(*) AS total_bookings,
  SUM(CASE WHEN bwf.is_fraud THEN 1 ELSE 0 END) AS fraud_count,
  ROUND(SUM(CASE WHEN bwf.is_fraud THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS fraud_rate_pct
FROM bookings_with_fraud bwf
JOIN payments p ON bwf.booking_id = p.booking_id
GROUP BY bwf.guests_count, p.payment_method;
