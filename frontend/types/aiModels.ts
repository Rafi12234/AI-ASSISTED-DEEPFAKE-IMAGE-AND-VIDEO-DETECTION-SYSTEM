export type ProductionModelEvidence = {
  id: string | null;
  analysis_result_id: string;
  model_name: string;
  model_version: string;
  model_type: string;
  input_type: string;
  score: number;
  confidence: number | null;
  latency_ms: number | null;
  device: string;
  details: Record<string, unknown>;
  created_at: string | null;
};

export type ProductionForensicEvidence = {
  id: string;
  analysis_result_id: string;
  signal_type: string;
  signal_name: string | null;
  score: number | null;
  severity: string | null;
  description: string | null;
  raw_data: Record<string, unknown>;
  created_at: string | null;
};

export type ProductionEvidenceResponse = {
  result_id: string;
  job_id: string;
  upload_id: string;

  media: {
    filename: string;
    file_type: string;
    mime_type: string;
  };

  summary: {
    final_score: number;
    risk_level: string;
    confidence: number;
    processing_time_ms: number | null;
    engine: string | null;
    pipeline_version: string | null;
  };

  interpretation: {
    verdict?: string;
    score_interpretation?: string;
    recommended_action?: string;
    limitations?: string[];
    human_summary?: string;
  };

  model_versions: {
    engine?: string;
    models?: Array<{
      model_name: string;
      model_version: string;
    }>;
  };

  production_pipeline: {
    pipeline_version?: string;
    media_type?: string;
    model_evidence_count?: number;
    forensic_evidence_count?: number;
    note?: string;
  };

  model_evidence: ProductionModelEvidence[];
  forensic_evidence: ProductionForensicEvidence[];

  face_evidence: Array<Record<string, unknown>>;
  frame_evidence: Array<Record<string, unknown>>;
  audio_evidence: Record<string, unknown> | null;

  raw_signals_summary: Record<string, unknown>;
};