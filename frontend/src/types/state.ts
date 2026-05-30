export type PageMode =
  | 'empty'
  | 'ready'
  | 'analyzing'
  | 'analyzed'
  | 'dirty'
  | 'failed';

export type AnalysisStatus =
  | 'none'
  | 'running'
  | 'success'
  | 'partial'
  | 'failed'
  | 'cancelled'
  | 'timeout';

export type TrustStatus =
  | 'trusted'
  | 'stale'
  | 'untrusted';

export type StaleReason =
  | 'sql_changed'
  | 'metadata_changed'
  | 'analysis_expired';

export interface WorkbenchRuntimeState {
  pageMode: PageMode;
  analysisStatus: AnalysisStatus;
  trustStatus: TrustStatus;
  analysisId?: string;
  sqlHash?: string;
  metadataVersion?: string;
  staleReason?: StaleReason;
  lastTrustedAnalysisId?: string;
  lastTrustedSqlHash?: string;
}
