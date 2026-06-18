export type UploadResponse = {
  upload_id: string;
  job_id: string;
  original_filename: string;
  file_type: string;
  mime_type: string;
  file_size_bytes: number;
  stored_path: string;
  upload_status: string;
  analysis_status: string;
  message?: string;
};

export type MyUpload = {
  upload_id: string;
  job_id?: string | null;
  original_filename: string;
  file_type: string;
  mime_type: string;
  file_size_bytes: number;
  upload_status: string;
  analysis_status?: string | null;
  created_at: string;
};