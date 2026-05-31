-- GC-P2-002: window_function
-- 窗口函数血缘 - 验证 PARTITION BY / ORDER BY 列提取
-- 期望: expression 节点包含 ROW_NUMBER() OVER (...)，source columns 包含 user_id 和 order_amt

SELECT
  user_id,
  order_amt,
  ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_amt DESC) AS rn
FROM default.order_table
