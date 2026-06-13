export type UploadResponse = {
  upload_id: string;
  job_id: string;
  original_filename: string;
  file_type: string;
  mime_type: string;
  file_size_bytes: number;
  upload_status: string;
  analysis_status: string;
};

export type UploadDetail = {
  id: string;
  original_filename: string;
  file_type: string;
  mime_type: string;
  file_size_bytes: number;
  upload_status: string;
  is_deleted: boolean;
  created_at: string;
};

export type UploadListResponse = {
  uploads: UploadDetail[];
};