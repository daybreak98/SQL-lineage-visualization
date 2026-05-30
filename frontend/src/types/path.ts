export interface PathRef {
  nodes: string[];
  edges: string[];
}

export interface PathContextStore {
  selectedOutputEntityId?: string;
  selectedOutputDisplayName?: string;

  pathMode: 'none' | 'upstream' | 'downstream' | 'full';

  pathStatus:
    | 'idle'
    | 'ready'
    | 'partial'
    | 'stale'
    | 'low_confidence'
    | 'failed';

  pathRef?: PathRef;

  nodeCount?: number;
  mappingCount?: number;
  warningCount?: number;
  unresolvedCount?: number;

  confidenceLevel?: 'high' | 'medium' | 'low' | 'unknown';

  staleReason?: 'sql_changed' | 'metadata_changed' | 'analysis_expired';
}
