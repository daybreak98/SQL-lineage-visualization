-- RS-P0-002: user_order_join
-- 真实场景: 用户+订单关联查询
-- 模拟数仓日常的维表关联，获取用户名称与订单信息
-- P0 范围: 两表 LEFT JOIN + 显式表别名消歧字段投影

select
    a.order_no,
    a.order_amt,
    a.status,
    b.user_name
from default.order_table a
left join default.user_table b
    on a.user_id = b.user_id
where a.dt = '2026-05-29'
