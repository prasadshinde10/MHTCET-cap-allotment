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
  states?: string[];
  cities?: string[];
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
  counselling_type?: string;
  academic_year?: string;
  round_name?: string;
  college_id?: number;
  college_name?: string;
  course_id?: number;
  course_name?: string;
  college_type?: string;
  state?: string;
  city?: string;
  category?: string;
  quota?: string;
  gender?: string;
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
  mcc_cutoff_count?: number;
  state_cutoff_count?: number;
}

// Fetch filter options from medical.db
export const getMedicalFilterOptions = async (
  counsellingType?: string
): Promise<MedicalFilterOptions> => {
  const response = await apiClient.get<MedicalFilterOptions>('/medical/filter-options', {
    params: counsellingType ? { counselling_type: counsellingType } : undefined,
  });
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
  if (params.counselling_type) searchParams.set('counselling_type', params.counselling_type);
  if (params.academic_year) searchParams.set('academic_year', params.academic_year);
  if (params.round_name) searchParams.set('round_name', params.round_name);
  if (params.college_name) searchParams.set('college_name', params.college_name);
  if (params.course_name) searchParams.set('course_name', params.course_name);
  if (params.college_type) searchParams.set('college_type', params.college_type);
  if (params.state) searchParams.set('state', params.state);
  if (params.city) searchParams.set('city', params.city);
  if (params.category) searchParams.set('category', params.category);
  if (params.quota) searchParams.set('quota', params.quota);
  if (params.gender) searchParams.set('gender', params.gender);
  if (params.student_rank) searchParams.set('student_rank', params.student_rank.toString());
  if (params.student_score) searchParams.set('student_score', params.student_score.toString());
  if (params.sort_by) searchParams.set('sort_by', params.sort_by);

  const baseUrl = apiClient.defaults.baseURL || '/api';
  return `${baseUrl}/medical/export?${searchParams.toString()}`;
};

// Wipe medical database
export const resetMedicalDatabase = async (counsellingType?: string): Promise<{ success: boolean; message: string }> => {
  const url = counsellingType ? `/medical/wipe?counselling_type=${counsellingType}` : '/medical/wipe';
  const response = await apiClient.post<{ success: boolean; message: string }>(url);
  return response.data;
};

export interface MedicalDbStatus {
  cutoff_count: number;
  college_count: number;
  course_count: number;
  years: string[];
  has_backup: boolean;
}

export interface MedicalUploadResult {
  success: boolean;
  filename: string;
  stream_type: string;
  academic_year: string;
  round_name: string;
  records_created: number;
  total_cutoffs: number;
  total_colleges: number;
  total_courses: number;
  duration_seconds: number;
  message: string;
}

export interface MedicalUploadStartResponse {
  task_id: string;
  status: string;
  filename: string;
  total_pages: number;
  progress_percent: number;
  current_action: string;
  message: string;
}

export interface MedicalTaskProgress {
  task_id: string;
  filename: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  progress_percent: number;
  current_page: number;
  total_pages: number;
  records_created: number;
  current_action: string;
  error?: string | null;
  result?: MedicalUploadResult | null;
}

// Get DB Status
export const getMedicalDbStatus = async (): Promise<MedicalDbStatus> => {
  const response = await apiClient.get<MedicalDbStatus>('/medical/db-status');
  return response.data;
};

// Restore verified Medical dataset
export const restoreMedicalDatabase = async (counsellingType?: string): Promise<{
  success: boolean;
  message: string;
  cutoff_count: number;
  college_count: number;
  course_count: number;
}> => {
  const url = counsellingType ? `/medical/restore?counselling_type=${counsellingType}` : '/medical/restore';
  const response = await apiClient.post(url);
  return response.data;
};

// Upload Medical PDF and start background ingestion
export const uploadMedicalPdf = async (
  file: File,
  academicYear?: string,
  roundName?: string,
  streamType?: string
): Promise<MedicalUploadStartResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  if (academicYear) formData.append('academic_year', academicYear);
  if (roundName) formData.append('round_name', roundName);
  if (streamType) formData.append('stream_type', streamType);

  const response = await apiClient.post<MedicalUploadStartResponse>('/medical/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// Poll live progress for background ingestion task
export const getMedicalUploadProgress = async (
  taskId: string
): Promise<MedicalTaskProgress> => {
  const response = await apiClient.get<MedicalTaskProgress>(`/medical/upload/progress/${taskId}`);
  return response.data;
};

