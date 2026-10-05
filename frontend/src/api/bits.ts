import apiClient from './client';

export interface BitsCampusItem {
  id: number;
  campus_code: string;
  campus_name: string;
  location?: string | null;
  state?: string | null;
}

export interface BitsProgramItem {
  id: number;
  program_code?: string | null;
  program_name: string;
  degree_type: string;
}

export interface BitsFilterOptions {
  academic_years: string[];
  campuses: BitsCampusItem[];
  programs: BitsProgramItem[];
  degree_types: string[];
  categories: string[];
}

export interface BitsCutoffItem {
  id: number;
  academic_year: string;
  cutoff_score: number;
  max_marks: number;
  score_percentage?: number | null;
  category: string;
  exam_name: string;
  campus_id: number;
  campus_code: string;
  campus_name: string;
  campus_location?: string | null;
  campus_state?: string | null;
  program_id: number;
  program_code?: string | null;
  program_name: string;
  degree_type: string;
}

export interface BitsPaginatedResponse {
  items: BitsCutoffItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface BitsCutoffParams {
  academic_year?: string;
  campus_id?: number;
  campus_name?: string;
  program_id?: number;
  program_name?: string;
  degree_type?: string;
  min_score?: number;
  max_score?: number;
  student_score?: number;
  page?: number;
  page_size?: number;
  sort_by?: string;
}

export interface BitsDbStats {
  total_cutoffs: number;
  total_campuses: number;
  total_programs: number;
  available_years: string[];
  last_scraped_at?: string | null;
}

export interface BitsScraperStatus {
  is_running: boolean;
  status: 'IDLE' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  progress_percent: number;
  message: string;
  records_count: number;
  years_count: number;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
}

export const getBitsFilterOptions = async (): Promise<BitsFilterOptions> => {
  const response = await apiClient.get<BitsFilterOptions>('/bits/filter-options');
  return response.data;
};

export const getBitsCutoffs = async (params: BitsCutoffParams): Promise<BitsPaginatedResponse> => {
  const response = await apiClient.get<BitsPaginatedResponse>('/bits/cutoffs', { params });
  return response.data;
};

export const getBitsStats = async (): Promise<BitsDbStats> => {
  const response = await apiClient.get<BitsDbStats>('/bits/stats');
  return response.data;
};

export const getBitsExportUrl = (params: BitsCutoffParams): string => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, String(val));
    }
  });
  const baseURL = apiClient.defaults.baseURL || '/api';
  return `${baseURL}/bits/export?${query.toString()}`;
};

export const scrapeBitsData = async (years?: string[]): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post<{ success: boolean; message: string }>('/bits/scrape', null, {
    params: years ? { years } : {},
  });
  return response.data;
};

export const getBitsScraperStatus = async (): Promise<BitsScraperStatus> => {
  const response = await apiClient.get<BitsScraperStatus>('/bits/scraper-status');
  return response.data;
};

export const resetBitsDatabase = async (): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post<{ success: boolean; message: string }>('/bits/reset-database');
  return response.data;
};
