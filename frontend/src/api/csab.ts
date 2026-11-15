import apiClient from './client';

export interface CsabInstituteItem {
  id: number;
  institute_code?: string | null;
  institute_name: string;
  institute_type: string;
  state?: string | null;
}

export interface CsabProgramItem {
  id: number;
  program_code?: string | null;
  program_name: string;
  degree_type?: string | null;
}

export interface CsabCategoryItem {
  id: number;
  category_code: string;
  category_name?: string | null;
}

export interface CsabFilterOptions {
  rounds: number[];
  years: number[];
  institute_types: string[];
  institutes: CsabInstituteItem[];
  programs: CsabProgramItem[];
  categories: CsabCategoryItem[];
  quotas: string[];
  genders: string[];
  states?: string[];
}

export interface CsabCutoff {
  id: number;
  academic_year: number;
  round_no: number;
  quota: string;
  gender: string;
  opening_rank: number;
  closing_rank: number;
  is_preparatory: boolean;
  institute_id: number;
  institute_code?: string | null;
  institute_name: string;
  institute_type: string;
  institute_state?: string | null;
  program_id: number;
  program_code?: string | null;
  program_name: string;
  degree_type?: string | null;
  category_id: number;
  category_code: string;
  category_name?: string | null;
}

export interface CsabCutoffResponse {
  items: CsabCutoff[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CsabCutoffParams {
  round_no?: string;
  institute_type?: string;
  institute_name?: string;
  institute_id?: number;
  state?: string;
  candidate_state?: string;
  academic_program?: string;
  program_id?: number;
  category?: string;
  quota?: string;
  gender?: string;
  academic_year?: number;
  max_rank?: number;
  page?: number;
  page_size?: number;
  sort_by?: string;
}

export const getCsabFilterOptions = async (): Promise<CsabFilterOptions> => {
  const response = await apiClient.get<CsabFilterOptions>('/csab/filter-options');
  return response.data;
};

export const getCsabCutoffs = async (params: CsabCutoffParams): Promise<CsabCutoffResponse> => {
  const response = await apiClient.get<CsabCutoffResponse>('/csab/cutoffs', { params });
  return response.data;
};

export const getCsabExportUrl = (params: CsabCutoffParams): string => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, String(val));
    }
  });
  const baseURL = apiClient.defaults.baseURL || '/api';
  return `${baseURL}/csab/export?${query.toString()}`;
};

export interface CsabDbStats {
  total_cutoffs: number;
  total_institutes: number;
  total_programs: number;
  total_categories: number;
}

export const getCsabStats = async (): Promise<CsabDbStats> => {
  const response = await apiClient.get<CsabDbStats>('/csab/stats');
  return response.data;
};

export const resetCsabDatabase = async (): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post<{ success: boolean; message: string }>('/csab/reset-database');
  return response.data;
};

export interface CsabScraperStatus {
  is_running: boolean;
  status: 'IDLE' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  progress_percent: number;
  current_round: number | null;
  message: string;
  records_round1: number;
  records_round2: number;
  total_records: number;
  total_rounds: number;
  completed_rounds: number;
  started_at: string | null;
  completed_at: string | null;
  error?: string | null;
}

export const getCsabScraperStatus = async (): Promise<CsabScraperStatus> => {
  const response = await apiClient.get<CsabScraperStatus>('/csab/scraper-status');
  return response.data;
};

export const scrapeCsabData = async (): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post<{ success: boolean; message: string }>('/csab/scrape');
  return response.data;
};
