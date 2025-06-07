-- "Customers with too much cash vs investments or vice versa"
CREATE MATERIALIZED VIEW portfolio_rebalancing_opportunities AS
SELECT
  bt.customer_id,
  SUM(bt.avg_amount) as cash_position,
  SUM(nw.total_net_worth) as investment_position,
  ROUND(SUM(bt.avg_amount) / (SUM(bt.avg_amount) + SUM(nw.total_net_worth)) * 100, 1) as cash_percentage,
  CASE
    WHEN SUM(bt.avg_amount) > SUM(nw.total_net_worth) * 0.5 THEN 'Too Much Cash - Suggest Investment'
    WHEN SUM(bt.avg_amount) < SUM(nw.total_net_worth) * 0.05 THEN 'Cash Poor - Suggest Liquidity Products'
    ELSE 'Balanced Portfolio'
  END as rebalancing_recommendation,
  -- Opportunity sizing
  CASE
    WHEN SUM(bt.avg_amount) > SUM(nw.total_net_worth) * 0.5 THEN SUM(bt.avg_amount) * 0.3 -- Move 30% to investments
    WHEN SUM(bt.avg_amount) < SUM(nw.total_net_worth) * 0.05 THEN SUM(nw.total_net_worth) * 0.1 -- Liquidate 10% for cash
    ELSE 0
  END as suggested_rebalancing_amount,
  c.campaign_name
FROM
  banking_summary bt
    INNER JOIN customer_net_worth nw
      ON bt.customer_id = nw.customer_id
    INNER JOIN finance_summit.ingestion.campaign c
      ON bt.customer_id = c.customer_id
WHERE
  bt.avg_amount > 2000
  AND nw.total_net_worth > 5000
GROUP BY
  bt.customer_id, c.campaign_name;