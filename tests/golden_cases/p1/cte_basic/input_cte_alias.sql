-- P1 CTE Basic: CTE with column alias
WITH mt AS (
  SELECT order_no AS order_id, user_id
  FROM default.order_table
)
SELECT order_id, user_id FROM mt
