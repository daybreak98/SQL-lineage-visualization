-- P1 Join Basic: equi-join on user_id (exists in both tables)
SELECT user_id
FROM default.order_table o
JOIN default.user_table u ON o.user_id = u.user_id
