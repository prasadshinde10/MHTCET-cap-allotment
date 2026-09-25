export interface CollegeOption {
  college_code: string;
  college_name: string;
  city?: string;
  district?: string;
}

export interface CourseOption {
  course_code: string;
  course_name: string;
}

export interface FilterOptions {
  years: number[];
  rounds: number[];
  categories: string[];
  seat_sections: string[];
  stages: string[];
  cities_districts: string[];
  colleges: CollegeOption[];
  courses: CourseOption[];
}

export interface CutoffSummary {
  total_matches: number;
  min_percentile?: number;
  max_percentile?: number;
  avg_percentile?: number;
  min_merit?: number;
  max_merit?: number;
  unique_colleges: number;
  unique_courses: number;
}

export interface RoundComparisonItem {
  course_code: string;
  course_name: string;
  college_name: string;
  category_code: string;
  seat_section: string;
  stage: string;
  round_a_merit?: number;
  round_a_percentile?: number;
  round_b_merit?: number;
  round_b_percentile?: number;
  percentile_change?: number;
}

export interface RoundComparison {
  course_id: number;
  course_name: string;
  college_name: string;
  category: string;
  round_1_score?: number;
  round_2_score?: number;
  round_3_score?: number;
  diff_1_2?: number;
  diff_2_3?: number;
}

