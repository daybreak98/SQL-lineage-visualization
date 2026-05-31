-- P1 Union All: union with same table, different partitions
SELECT order_no, user_id, order_amt
FROM default.order_table
WHERE dt = '20260529'
UNION ALL
SELECT order_no, user_id, order_amt
FROM default.order_table
WHERE dt = '20260528'
