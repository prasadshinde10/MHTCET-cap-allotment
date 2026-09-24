export interface Cutoff {
  id: number;
  year: number;
  cap_round_id: number;
  course_id: number;
  seat_section: string;
  category_code: string;
  gender?: string;
  seat_category?: string;
  seat_location?: string;
  stage: string;
  merit_number?: number;
  percentile?: number;
  source_page?: number;
  source_pdf?: string;
  is_manually_corrected?: boolean;
  is_deleted?: boolean;
  college_code?: string;
  college_name?: string;
  city?: string;
  district?: string;
  course_code?: string;
  course_name?: string;
  round_number?: number;
  created_at?: string;
  updated_at?: string;
}

export interface CutoffFilters {
  page?: number;
  page_size?: number;
  year?: number;
  round_number?: number;
  cap_round_id?: number;
  college?: string;
  college_code?: string;
  course?: string;
  course_code?: string;
  category_code?: string;
  gender?: string;
  city_district?: string;
  seat_section?: string;
  stage?: string;
  min_percentile?: number;
  max_percentile?: number;
  min_merit?: number;
  max_merit?: number;
  sort_by?: string;
  is_deleted?: boolean;
}

