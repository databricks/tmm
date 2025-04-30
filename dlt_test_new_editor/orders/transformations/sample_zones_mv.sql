-- This file defines a sample transformation.
-- Edit the sample below or add new transformations
-- using "+ Add" in the file browser.

CREATE MATERIALIZED VIEW new_transformation AS
SELECT *
FROM demo_frank.test.sample_trips_orders
