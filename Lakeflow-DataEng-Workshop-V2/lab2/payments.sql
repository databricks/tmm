CREATE OR REFRESH STREAMING TABLE payments
COMMENT 'Payments stream from samples.wanderbricks.payments'
AS SELECT
    payment_id,
    booking_id,
    amount,
    payment_method,
    status,
    payment_date
FROM stream(samples.wanderbricks.payments);
