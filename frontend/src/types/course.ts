export interface Course {
  id: number;
  course_code: string;
  course_name: string;
  college_id: number;
  college_name?: string;
  college_code?: string;
  cutoff_count?: number;
  created_at?: string;
  updated_at?: string;
}
