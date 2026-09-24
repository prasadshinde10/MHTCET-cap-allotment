export interface RecentImport {
  filename: string;
  round_name: string;
  year: number;
  status: string;
  records: number;
  date: string | null;
}

export interface RecentError {
  page: number | null;
  error: string;
  severity: string;
  status: string;
}

export interface DashboardStats {
  total_colleges: number;
  total_courses: number;
  total_cutoffs: number;
  rounds_processed: number;
  total_imports: number;
  successful_imports: number;
  warning_imports: number;
  failed_imports: number;
  open_parser_errors: number;
  cap_round_1_records: number;
  cap_round_2_records: number;
  cap_round_3_records: number;
  cap_round_4_records: number;
  recent_imports: RecentImport[];
  recent_errors: RecentError[];
}
