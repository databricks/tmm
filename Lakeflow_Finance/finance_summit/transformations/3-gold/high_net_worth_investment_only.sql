-- Our data pipeline automatically spots Sarah as a "High Net Worth" prospect who doesn't have a banking relationship with us. The system calculates she could generate ~$18,000 in annual banking revenue.

CREATE MATERIALIZED VIEW finance_summit.pipeline.high_value_investment_prospects
AS
SELECT 
    nw.customer_id,
    nw.total_net_worth,
    CASE 
        WHEN nw.total_net_worth > 5000000 THEN 'Ultra High Net Worth'
        WHEN nw.total_net_worth > 2000000 THEN 'High Net Worth'
        WHEN nw.total_net_worth > 1000000 THEN 'Affluent'
        ELSE 'Mass Affluent'
    END as wealth_segment,
    ROUND(nw.total_net_worth * 0.015, 0) as estimated_annual_revenue_opportunity
FROM finance_summit.pipeline.customer_net_worth nw
-- The JOIN is essentially asking: Who invests with us but doesn't bank with us?
LEFT JOIN banking_customer b ON nw.customer_id = b.customer_id
WHERE b.customer_id IS NULL AND nw.total_net_worth > 500000;