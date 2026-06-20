export type SampledFrameResult = {
  frame_number: number;
  timestamp_seconds: number | null;
  final_score: number;
  risk_level: string;
  confidence: number;
};

export type AnalysisJob = {
  job_id: string;
  job_status: string;
  upload_id: string;
  queued_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  original_filename: string;
  file_type: string;
  mime_type: string;
  file_size_bytes: number;
  upload_status: string;
  uploaded_at: string;
};

export type AnalysisResult = {
  id: string;
  media_upload_id: string;
  analysis_job_id: string;
  final_score: number;
  risk_level: string;
  confidence: number;
  explanation: string;
  signals_summary: {
    summary?: string;
    prediction_count?: number;
    forensic_signal_count?: number;
    sampled_frames?: SampledFrameResult[];
    signals?: Array<{
      score: number;
      severity: string;
      description: string;
      signal_name: string;
      signal_type: string;
      raw_data?: Record<string, unknown>;
    }>;
  };
  model_versions: {
    engine?: string;
    models?: Array<{
      model_name: string;
      model_version: string;
    }>;
  };
  processing_time_ms: number | null;
  created_at: string;
};

export type ModelPrediction = {
  id: string;
  analysis_result_id: string;
  model_name: string;
  model_version: string;
  raw_score: number;
  calibrated_score: number;
  prediction_label: string;
  target_region: string | null;
  inference_time_ms: number | null;
  created_at: string;
};

export type ForensicSignal = {
  id: string;
  analysis_result_id: string;
  signal_type: string;
  signal_value: string | null;
  risk_contribution: number | null;
  details: {
    raw_data?: Record<string, unknown>;
    severity?: string;
    description?: string;
    signal_name?: string;
  };
  created_at: string;
};

export type AnalysisResultResponse = {
  job: AnalysisJob;
  result: AnalysisResult | null;
  model_predictions: ModelPrediction[];
  forensic_signals: ForensicSignal[];
  message?: string;
};