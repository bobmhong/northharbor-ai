export interface StartInterviewResponse {
  session_id: string;
  plan_id: string;
  message: string;
  interview_complete: boolean;
}

export interface RespondResponse {
  message: string;
  applied_fields: string[];
  rejected_fields: string[];
  interview_complete: boolean;
  missing_fields: string[];
}

export interface PlanSummary {
  plan_id: string;
  owner_id: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface StageResult {
  stage: string;
  status: "success" | "skipped" | "failed";
  duration_ms: number;
  artifact_ids: string[];
  errors: string[];
}

export interface PipelineOutputs {
  metrics: Record<string, unknown>;
  tables: TableSpec[];
  chart_specs: ChartSpec[];
  recommendations: Recommendation[];
  derived_fields: Record<string, unknown>;
  monte_carlo_results: Record<string, unknown>;
  backtest_results: Record<string, unknown>;
  what_if_results: Record<string, unknown>;
}

export interface PipelineResult {
  pipeline_id: string;
  plan_id: string;
  owner_id: string;
  schema_snapshot_id: string;
  started_at: string;
  completed_at: string | null;
  stages: StageResult[];
  outputs: PipelineOutputs;
}

export interface ChartSpec {
  id: string;
  title: string;
  chart_type: string;
  description: string;
  echarts_option: Record<string, unknown>;
  data_source: string;
  section: string;
}

export interface TableSpec {
  id: string;
  title: string;
  columns: { key: string; label: string; format: string }[];
  rows: Record<string, unknown>[];
  section: string;
}

export interface Recommendation {
  rule_id: string;
  message: string;
  evidence: Record<string, unknown>;
}

export interface ReportArtifact {
  report_id: string;
  plan_id: string;
  pipeline_id: string;
  generated_at: string;
  format: string;
  metrics: Record<string, unknown>;
  tables: TableSpec[];
  chart_specs: ChartSpec[];
  recommendations: Recommendation[];
  ai_analysis: AIAnalysis | null;
}

export interface AIAnalysis {
  interpretation: string;
  key_tradeoffs: string[];
  suggested_next_steps: string[];
  confidence_notes: string[];
  disclaimer: string;
}
