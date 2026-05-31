-- P1 CTE Basic: simple CTE with field traceback
WITH mt AS (
  SELECT order_no, user_id, order_amt
  FROM default.order_table
  WHERE dt = '20260513'
)
SELECT order_no, user_id, order_amt
FROM mt
