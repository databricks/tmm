-- Grant Service Principal permission to use the SQL Warehouse
-- Run this in your Databricks SQL editor

-- Grant USE permission on the SQL Warehouse to the Service Principal
-- Replace with your Service Principal ID
GRANT USE ON WAREHOUSE `a986f6d81a971b20` TO `4ec3b66b-001a-4486-8897-0ebf0ba89015`;

-- Alternative: Grant to all users (less secure but easier for testing)
-- GRANT USE ON WAREHOUSE `a986f6d81a971b20` TO `account users`;

-- Verify the grant
SHOW GRANTS ON WAREHOUSE `a986f6d81a971b20`;