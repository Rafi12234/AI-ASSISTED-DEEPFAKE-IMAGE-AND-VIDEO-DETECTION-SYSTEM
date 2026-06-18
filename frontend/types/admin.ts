export type AdminOverview = {
  uploads: {
    total_uploads: number;
  };
  jobs: {
    total_jobs: number;
    queued_jobs: number;
    processing_jobs: number;
    completed_jobs: number;
    failed_jobs: number;
  };
  results: {
    total_results: number;
    likely_authentic_count: number;
    uncertain_count: number;
    suspicious_count: number;
    high_risk_count: number;
  };
};

export type AdminJobItem = {
  job_id: string;
  job_status: string;
  queued_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;

  upload_id: string;
  original_filename: string;
  file_type: string;
  mime_type: string;
  file_size_bytes: number;
  upload_status: string;
  uploaded_at: string;

  user_id: string;
  user_email: string;

  result_id: string | null;
  final_score: number | null;
  risk_level: string | null;
  confidence: number | null;
  result_created_at: string | null;
};