-- Please edit the sample below

CREATE STREAMING TABLE
    banking_customer
AS SELECT
    *
FROM STREAM mrasooli.xsell.banking_customers
