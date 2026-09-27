import apiClient from './client';

export interface JosaaInstituteItem {
  id: number;
  institute_code?: string | null;
  institute_name: string;
  institute_type: string;
  state?: string | null;
}

export interface JosaaProgramItem {
  id: number;
  program_code?: string | null;
  program_name: string;
  degree_type?: string | null;
}

export interface JosaaCategoryItem {
  id: number;
  category_code: string;
  category_name?: string | null;
}

export interface JosaaFilterOptions {
  rounds: number[];
  years: number[];
  institute_types: string[];
  institutes: JosaaInstituteItem[];
  programs: JosaaProgramItem[];
  categories: JosaaCategoryItem[];
  quotas: string[];
  genders: string[];
}

export interface JosaaCutoff {
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

export interface JosaaCutoffResponse {
  items: JosaaCutoff[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface JosaaCutoffParams {
  round_no?: number;
  institute_type?: string;
  institute_name?: string;
  institute_id?: number;
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

export const getJosaaFilterOptions = async (): Promise<JosaaFilterOptions> => {
  const response = await apiClient.get<JosaaFilterOptions>('/josaa/filter-options');
  return response.data;
};

export const getJosaaCutoffs = async (params: JosaaCutoffParams): Promise<JosaaCutoffResponse> => {
  const response = await apiClient.get<JosaaCutoffResponse>('/josaa/cutoffs', { params });
  return response.data;
};

export const getJosaaExportUrl = (params: JosaaCutoffParams): string => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, String(val));
    }
  });
  const baseURL = apiClient.defaults.baseURL || '/api';
  return `${baseURL}/josaa/export?${query.toString()}`;
};

export interface JosaaDbStats {
  total_cutoffs: number;
  total_institutes: number;
  total_programs: number;
  total_categories: number;
}

export const getJosaaStats = async (): Promise<JosaaDbStats> => {
  const response = await apiClient.get<JosaaDbStats>('/josaa/stats');
  return response.data;
};

export const resetJosaaDatabase = async (): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post<{ success: boolean; message: string }>('/josaa/reset-database');
  return response.data;
};

export const reloadJosaaData = async (): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post<{ success: boolean; message: string }>('/josaa/reload-data');
  return response.data;
};

export const scrapeJosaaData = async (): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post<{ success: boolean; message: string }>('/josaa/scrape');
  return response.data;
};

