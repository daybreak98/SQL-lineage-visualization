-- GC-M24-001: cte_location
-- CTE 定义定位 golden case
-- 期望: source_locations 包含 with:scope:root (cte) 和 cte:scope:root:mt (cte)

WITH mt AS (
  SELECT agent_id, SUM(order_amount) AS gmv
  FROM intl_hotel_orders
  GROUP BY agent_id
),
t2 AS (
  SELECT agent_id, gmv
  FROM mt
  WHERE gmv > 1000
)
SELECT agent_id, gmv
FROM t2
