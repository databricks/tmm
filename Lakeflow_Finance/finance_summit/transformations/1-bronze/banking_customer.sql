-- Please edit the sample below

CREATE STREAMING TABLE
    banking_transactions
AS SELECT
    *
FROM STREAM mrasooli.xsell.banking_transactions