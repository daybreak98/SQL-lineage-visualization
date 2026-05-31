-- P1 Union All: union with constants
SELECT order_no, 1 AS flag
FROM default.order_table
WHERE dt = '20260529'
UNION ALL
SELECT order_no, 2 AS flag
FROM default.order_table
WHERE dt = '20260528'
