import apiClient from './client';

export interface IiserInstituteItem {
  id: number;
  institute_code?: string | null;
  institute_name: string;
  state?: string | null;
}

export interface IiserProgramItem {
  id: number;
  program_code?: string | null;
  program_name: string;
  degree_type: string;
}

export interface IiserCategoryItem {
  id: number;
  category_code: string;
  category_name: string;
  is_pwd: boolean;
}

export interface IiserFilterOptions {
  rounds: number[];
  years: number[];
  institutes: IiserInstituteItem[];
  programs: IiserProgramItem[];
  degree_types: string[];
  categories: IiserCategoryItem[];
  states: string[];
}

export interface IiserCutoffItem {
  id: number;
  academic_year: number;
  round_no: number;
  raw_program_name: string;
  closing_rank: number;
  seat_pool: string;
  allocation_channel: string;
  institute_id: number;
  institute_code?: string | null;
  institute_name: string;
  institute_state?: string | null;
  program_id: number;
  program_code?: string | null;
  program_name: string;
  degree_type: string;
  category_id: number;
  category_code: string;
  category_name: string;
  is_pwd: boolean;
}

export interface IiserPaginatedResponse {
  items: IiserCutoffItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface IiserCutoffParams {
  round_no?: string;
  academic_year?: number;
  institute_id?: number;
  institute_name?: string;
  state?: string;
  program_id?: number;
  academic_program?: string;
  degree_type?: string;
  category?: string;
  max_rank?: number;
  page?: number;
  page_size?: number;
  sort_by?: string;
}

export interface IiserRoundNoticeItem {
  id: number;
  academic_year: number;
  round_no: number;
  notice_text: string;
  created_at?: string | null;
}

export interface IiserDbStats {
  total_cutoffs: number;
  total_institutes: number;
  total_programs: number;
  total_categories: number;
  total_rounds: number;
  total_notices: number;
  last_scraped_at?: string | null;
}

export interface IiserScraperStatus {
  is_running: boolean;
  status: 'IDLE' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  progress_percent: number;
  current_round?: number | null;
  message: string;
  records_count: number;
  total_rounds: number;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
}

export const getIiserFilterOptions = async (): Promise<IiserFilterOptions> => {
  const response = await apiClient.get<IiserFilterOptions>('/iiser/filter-options');
  return response.data;
};

export const getIiserCutoffs = async (params: IiserCutoffParams): Promise<IiserPaginatedResponse> => {
  const response = await apiClient.get<IiserPaginatedResponse>('/iiser/cutoffs', { params });
  return response.data;
};

export const getIiserNotices = async (round_no?: number): Promise<IiserRoundNoticeItem[]> => {
  const response = await apiClient.get<IiserRoundNoticeItem[]>('/iiser/notices', {
    params: round_no ? { round_no } : {},
  });
  return response.data;
};

export const getIiserStats = async (): Promise<IiserDbStats> => {
  const response = await apiClient.get<IiserDbStats>('/iiser/stats');
  return response.data;
};

export const getIiserExportUrl = (params: IiserCutoffParams): string => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, String(val));
    }
  });
  const baseURL = apiClient.defaults.baseURL || '/api';
  return `${baseURL}/iiser/export?${query.toString()}`;
};

export const scrapeIiserData = async (): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post<{ success: boolean; message: string }>('/iiser/scrape');
  return response.data;
};

export const getIiserScraperStatus = async (): Promise<IiserScraperStatus> => {
  const response = await apiClient.get<IiserScraperStatus>('/iiser/scraper-status');
  return response.data;
};

export const resetIiserDatabase = async (): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post<{ success: boolean; message: string }>('/iiser/reset-database');
  return response.data;
};
