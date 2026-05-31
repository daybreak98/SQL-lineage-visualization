-- GC-P2-002: join_expansion_risk
-- 多表 JOIN - 验证口径报告能否识别 JOIN 关系和放大风险
-- 期望 semantics_report: joins 非空, semantic_risks 包含 join_amplification

SELECT o.order_no, u.user_name 
FROM order_table o 
JOIN user_table u ON o.user_id = u.user_id
