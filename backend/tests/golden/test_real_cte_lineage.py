import time

from app.domain.contracts import AnalysisOptions, AnalyzeSqlRequest, Dialect
from app.services.analysis_orchestrator import AnalysisOrchestrator


REALISTIC_CTE_SQL = """
with ab_rule as (
    select ab_exp_id, ab_version, ab_rule_version, device_id as ab_exp_value
    from default.ods_abtest_rule_info
),
search_list as (
    select *
    from (
        select
            concat(substr(a.dt,1,4),'-',substr(a.dt,5,2),'-',substr(a.dt,7,2)) as datee,
            a.search_request_uid,
            a.orig_device_id,
            a.is_display,
            a.hotel_seq,
            a.detail_log_id,
            a.qpayprice,
            case when a.is_display = '1' then a.rank else null end as click_rank
        from default.dwd_ihotel_flow_app_searchlist_di a
    ) s
    where s.datee is not null
),
order_detail as (
    select
        a.order_date as datee,
        a.user_info['orig_device_id'] as orig_device_id,
        a.init_gmv,
        a.room_night,
        cast(init_commission_after + nvl(ext_plat_certificate, 0) as decimal(20,0)) as order_commission
    from default.mdw_order_v3_international a
),
search_result as (
    select
        a.datee,
        a.ab_version,
        a.ab_rule_version,
        count(distinct a.search_request_uid) as search_times,
        count(distinct case when a.is_display = '1' then a.orig_device_id else null end) as show_uv,
        avg(case when a.is_display = '1' then a.qpayprice else null end) as show_adr
    from (
        select *
        from ab_rule
        left join search_list
          on ab_rule.ab_exp_value = search_list.orig_device_id
    ) a
    group by 1,2,3
),
order_result as (
    select
        a.datee,
        a.ab_version,
        a.ab_rule_version,
        sum(a.init_gmv) as total_gmv,
        sum(a.room_night) as total_room_night,
        sum(a.init_gmv) / sum(a.room_night) as order_adr,
        sum(a.order_commission) as total_order_commission
    from (
        select *
        from ab_rule
        left join order_detail
          on ab_rule.ab_exp_value = order_detail.orig_device_id
    ) a
    group by 1,2,3
)
select
    a.datee,
    a.ab_version,
    a.ab_rule_version,
    cast(b.total_order_commission / a.show_uv as decimal(20,2)) as uv_revenue,
    concat(round(a.search_times / a.show_uv * 100, 2), '%') as s2d,
    cast(b.order_adr as decimal(20,2)) as order_adr,
    concat(round((a.show_adr / b.order_adr - 1) * 100, 2), '%') as adr_gap
from search_result a
join order_result b
  on a.datee = b.datee
 and a.ab_version = b.ab_version
 and a.ab_rule_version = b.ab_rule_version
"""


def _analyze():
    request = AnalyzeSqlRequest(
        sql=REALISTIC_CTE_SQL,
        dialect=Dialect.hive,
        analysis_options=AnalysisOptions(
            include_graph=True,
            include_semantics=False,
            include_source_location=True,
        ),
    )
    return AnalysisOrchestrator().analyze(request)


def _source_columns_for_output(result, output_name: str) -> set[str]:
    output_node = next(
        node for node in result.graph_view_model.nodes
        if node.node_type.value == "output_column" and node.label == output_name
    )
    direct_sources = {
        edge.source
        for edge in result.graph_view_model.edges
        if edge.target == output_node.id
    }
    expanded_sources = set(direct_sources)
    for source in direct_sources:
        expanded_sources.update(
            edge.source
            for edge in result.graph_view_model.edges
            if edge.target == source
        )
    return expanded_sources


def test_realistic_cte_sql_resolves_final_metric_upstream_tables():
    result = _analyze()

    assert result.summary.output_column_count == 7
    assert result.elapsed_ms < 5000

    uv_sources = _source_columns_for_output(result, "uv_revenue")
    assert "column:default.mdw_order_v3_international.init_commission_after" in uv_sources
    assert "column:default.mdw_order_v3_international.ext_plat_certificate" in uv_sources
    assert "column:default.dwd_ihotel_flow_app_searchlist_di.orig_device_id" in uv_sources

    s2d_sources = _source_columns_for_output(result, "s2d")
    assert "column:default.dwd_ihotel_flow_app_searchlist_di.search_request_uid" in s2d_sources
    assert "column:default.dwd_ihotel_flow_app_searchlist_di.orig_device_id" in s2d_sources

    order_adr_sources = _source_columns_for_output(result, "order_adr")
    assert "column:default.mdw_order_v3_international.init_gmv" in order_adr_sources
    assert "column:default.mdw_order_v3_international.room_night" in order_adr_sources

    adr_gap_sources = _source_columns_for_output(result, "adr_gap")
    assert "column:default.dwd_ihotel_flow_app_searchlist_di.qpayprice" in adr_gap_sources
    assert "column:default.mdw_order_v3_international.init_gmv" in adr_gap_sources
    assert "column:default.mdw_order_v3_international.room_night" in adr_gap_sources


def test_realistic_cte_sql_stays_under_five_seconds():
    start = time.perf_counter()
    result = _analyze()
    elapsed = time.perf_counter() - start

    assert result.elapsed_ms < 5000
    assert elapsed < 5


def test_unqualified_output_column_prefers_final_from_cte():
    sql = """
    with order_base as (
      select
        o.user_id,
        o.order_no,
        o.order_amount,
        u.country_name
      from dwd_order_di o
      left join dim_user_df u
        on o.user_id = u.user_id
    ),
    valid_order_subq as (
      select country_name, user_id, order_amount
      from order_base
    ),
    metric_base as (
      select country_name, count(distinct user_id) as user_cnt
      from valid_order_subq
      group by country_name
    )
    select country_name, user_cnt
    from metric_base
    """
    request = AnalyzeSqlRequest(
        sql=sql,
        dialect=Dialect.hive,
        analysis_options=AnalysisOptions(
            include_graph=True,
            include_semantics=False,
            include_source_location=False,
        ),
    )

    result = AnalysisOrchestrator().analyze(request)

    country_sources = _source_columns_for_output(result, "country_name")
    assert "column:default.dim_user_df.country_name" in country_sources
    assert "unknown:scope:root:1:country_name" not in country_sources
