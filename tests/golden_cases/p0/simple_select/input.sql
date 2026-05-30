-- GC-P0-001: simple_select
-- 单表字段直选 - 验证最基本的字段投影血缘
-- 期望 status=success, 2条 projection 边

select order_no, user_id from default.order_table
