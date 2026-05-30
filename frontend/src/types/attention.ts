export interface AttentionViewModel {
  primaryFocus:
    | 'empty_guide'
    | 'analyze'
    | 'search_default_output'
    | 'current_path'
    | 'detail_mapping'
    | 'monaco_range'
    | 're_analyze'
    | 'error_summary';

  taskStage:
    | 'empty'
    | 'ready'
    | 'analyzing'
    | 'analyzed_no_field'
    | 'path_selected'
    | 'object_selected'
    | 'locating_sql'
    | 'dirty'
    | 'failed';

  reason: string;

  source:
    | 'page_mode'
    | 'path_context'
    | 'selection'
    | 'diagnostic'
    | 'editor_dirty';
}
