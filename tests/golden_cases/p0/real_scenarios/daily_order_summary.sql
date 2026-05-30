-- RS-P0-001: daily_order_summary
-- 真实场景: 日订单汇总查询
-- 模拟数仓日常的订单维度聚合，按状态统计每日订单量
-- P0 范围: 简单字段投影 + GROUP BY 聚合（表级血缘可识别，字段级血缘在 P1 展开）

select
    dt,
    status,
    count(order_no) as order_cnt,
    sum(order_amt)  as total_amt
from default.order_table
where dt = '2026-05-29'
group by dt, status
order by status
