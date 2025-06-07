 -- streaming ingest from the Microsoft SQL Server change data feed
 
 CREATE OR REFRESH STREAMING TABLE banking_customer_cdf;
 APPLY CHANGES INTO
   banking_customer_cdf
 FROM
   STREAM(finance_summit.ingestion.banking_customer_cdf)
 KEYS (customer_id)
 APPLY AS DELETE WHEN
   operation_type = "DELETE"
 SEQUENCE BY
   seq
 COLUMNS * EXCEPT (seq)
 STORED AS SCD TYPE 1;