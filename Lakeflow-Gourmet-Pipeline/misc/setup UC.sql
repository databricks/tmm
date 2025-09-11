-- CREATE SCHEMA daiwt_gourmet ;
GRANT CREATE SCHEMA, USE SCHEMA, USE CATALOG on CATALOG daiwt_gourmet TO `account users`; 
GRANT USAGE, SELECT, EXECUTE ON SCHEMA daiwt_gourmet.virtual_event TO `account users`; 