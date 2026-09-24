export interface ParserError {
  id: number;
  import_job_id: number;
  page_number?: number;
  raw_text?: string;
  error_message: string;
  severity: string; // 'warning' | 'error' | 'critical'
  status: string; // 'open' | 'resolved' | 'ignored'
  resolved_by?: number;
  resolved_at?: string;
  resolution_notes?: string;
  created_at: string;
}
