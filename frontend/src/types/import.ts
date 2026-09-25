export interface UploadResponse {
  import_batch_id: number;
  cap_round_id: number;
  filename: string;
  file_hash: string;
  message: string;
}

export interface ImportBatch {
  id: number;
  cap_round_id: number;
  round_name: string | null;
  year: number | null;
  round_number: number | null;
  filename: string;
  status: string;
  pages_processed: number;
  records_created: number;
  records_rejected: number;
  warning_count: number;
  error_count: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ImportLog {
  id: number;
  level: string;
  message: string;
  page_number: number | null;
  created_at: string;
}

export interface ImportBatchDetail extends ImportBatch {
  file_hash: string;
  file_path: string | null;
  parser_version: string;
  summary: Record<string, any> | null;
  recent_logs: ImportLog[];
  error_summary: Record<string, number>;
}

export interface StagingCutoff {
  id: number;
  college_code: string;
  course_code: string;
  seat_section: string | null;
  category_code: string | null;
  stage: string | null;
  merit_number: number | null;
  percentile: number | null;
  source_page: number | null;
  validation_status: string | null;
}

export interface CommitResponse {
  records_committed: number;
  colleges_created: number;
  courses_created: number;
  message: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
