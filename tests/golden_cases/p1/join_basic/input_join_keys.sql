-- P1 Join Basic: multiple join keys
SELECT o.order_no, u.user_name
FROM default.order_table o
JOIN default.user_table u ON o.user_id = u.user_id
