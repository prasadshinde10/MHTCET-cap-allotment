export interface College {
  id: number;
  college_code: string;
  college_name: string;
  city?: string;
  district?: string;
  college_type?: string;
  funding_type?: string;
  minority_status?: string;
  minority_type?: string;
  home_university?: string;
  status: string;
  course_count?: number;
  created_at?: string;
  updated_at?: string;
}
