CREATE OR REFRESH STREAMING TABLE bookings_current
COMMENT 'Latest state of each booking, rebuilt from booking_updates via AutoCDC';

CREATE FLOW bookings_current_flow AS AUTO CDC INTO bookings_current
FROM stream(samples.wanderbricks.booking_updates)
KEYS (booking_id)
SEQUENCE BY updated_at
COLUMNS * EXCEPT (booking_update_id)
STORED AS SCD TYPE 1;
