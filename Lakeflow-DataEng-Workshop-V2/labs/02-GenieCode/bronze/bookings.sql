-- GENIE_CODE_GENERATED | 2026-05-17T13:34:00Z | CDC bookings from booking_updates

CREATE OR REFRESH STREAMING TABLE bookings
TBLPROPERTIES ('created_by' = 'genie_code', 'created_at' = '2026-05-17T13:34:00Z');

CREATE FLOW bookings_cdc_flow AS AUTO CDC INTO bookings
FROM STREAM(samples.wanderbricks.booking_updates)
KEYS (booking_id)
SEQUENCE BY booking_update_id
STORED AS SCD TYPE 1;
