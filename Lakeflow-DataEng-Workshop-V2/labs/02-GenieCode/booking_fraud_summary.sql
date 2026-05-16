CREATE OR REFRESH MATERIALIZED VIEW booking_fraud_summary
COMMENT 'Payment totals and fraud rate per payment method (gross_amount sums payment rows; a booking with multiple payments contributes each one)'
AS
WITH fraud_bookings AS (
    -- DISTINCT because the same booking can appear in multiple flag JSON files.
    SELECT DISTINCT booking_id
    FROM booking_fraud_flags
)
SELECT
    p.payment_method,
    COUNT(DISTINCT b.booking_id)                                                  AS booking_count,
    ROUND(SUM(p.amount), 2)                                                       AS gross_amount,
    COUNT(DISTINCT f.booking_id)                                                  AS fraud_count,
    ROUND(SUM(CASE WHEN f.booking_id IS NOT NULL THEN p.amount ELSE 0 END), 2)    AS fraud_amount,
    ROUND(COUNT(DISTINCT f.booking_id) * 100.0 / COUNT(DISTINCT b.booking_id), 2) AS fraud_pct
FROM bookings_current      b
JOIN payments              p ON p.booking_id = b.booking_id
LEFT JOIN fraud_bookings   f ON f.booking_id = b.booking_id
GROUP BY p.payment_method;
