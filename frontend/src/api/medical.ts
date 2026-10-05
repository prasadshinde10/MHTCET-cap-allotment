import apiClient from './client';

export interface MedicalCollegeItem {
  id: number;
  college_code: string;
  college_name: string;
  college_type?: string | null;
  city?: string | null;
  state?: string | null;
}

export interface MedicalCourseItem {
  id: number;
  course_code: string;
  course_name: string;
  degree_type: string;
}

export interface MedicalFilterOptions {
  academic_years: string[];
  rounds: string[];
  colleges: MedicalCollegeItem[];
  courses: MedicalCourseItem[];
  college_types: string[];
  categories: string[];
  quotas: string[];
}

export interface MedicalCutoffItem {
  id: number;
  academic_year: string;
  round: string;
  quota_category: string;
  base_category: string;
  opening_rank?: number | null;
  closing_rank?: number | null;
  opening_score?: number | null;
  closing_score?: number | null;
  allotted_seats: number;
  exam_name: string;
  chance?: 'High' | 'Medium' | 'Borderline' | 'Low' | null;
  college_id: number;
  college_code: string;
  college_name: string;
  college_type?: string | null;
  city?: string | null;
  state?: string | null;
  course_id: number;
  course_code: string;
  course_name: string;
  degree_type: string;
}

export interface MedicalPaginatedResponse {
  items: MedicalCutoffItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface MedicalCutoffParams {
  academic_year?: string;
  round_name?: string;
  college_id?: number;
  college_name?: string;
  course_id?: number;
  course_name?: string;
  college_type?: string;
  category?: string;
  quota?: string;
  student_rank?: number;
  student_score?: number;
  min_rank?: number;
  max_rank?: number;
  min_score?: number;
  max_score?: number;
  page?: number;
  page_size?: number;
  sort_by?: string;
}

export interface MedicalDbStats {
  cutoff_count: number;
  college_count: number;
  course_count: number;
  years: string[];
  college_types: Record<string, number>;
  courses_breakdown: Record<string, number>;
}

// Fetch filter options from medical.db
export const getMedicalFilterOptions = async (): Promise<MedicalFilterOptions> => {
  const response = await apiClient.get<MedicalFilterOptions>('/medical/filter-options');
  return response.data;
};

// Query cutoffs
export const getMedicalCutoffs = async (
  params: MedicalCutoffParams
): Promise<MedicalPaginatedResponse> => {
  const response = await apiClient.get<MedicalPaginatedResponse>('/medical/cutoffs', {
    params,
  });
  return response.data;
};

// Get stats
export const getMedicalStats = async (): Promise<MedicalDbStats> => {
  const response = await apiClient.get<MedicalDbStats>('/medical/stats');
  return response.data;
};

// Export CSV URL
export const getMedicalExportUrl = (params: MedicalCutoffParams): string => {
  const searchParams = new URLSearchParams();
  if (params.academic_year) searchParams.set('academic_year', params.academic_year);
  if (params.round_name) searchParams.set('round_name', params.round_name);
  if (params.college_name) searchParams.set('college_name', params.college_name);
  if (params.course_name) searchParams.set('course_name', params.course_name);
  if (params.college_type) searchParams.set('college_type', params.college_type);
  if (params.category) searchParams.set('category', params.category);
  if (params.quota) searchParams.set('quota', params.quota);
  if (params.student_rank) searchParams.set('student_rank', params.student_rank.toString());
  if (params.student_score) searchParams.set('student_score', params.student_score.toString());
  if (params.sort_by) searchParams.set('sort_by', params.sort_by);

  const baseUrl = apiClient.defaults.baseURL || '/api';
  return `${baseUrl}/medical/export?${searchParams.toString()}`;
};

// Wipe medical database
export const resetMedicalDatabase = async (): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post<{ success: boolean; message: string }>('/medical/wipe');
  return response.data;
};
