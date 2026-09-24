import apiClient from './client';
import { FilterOptions, CutoffSummary, RoundComparisonItem } from '../types/analysis';
import { CutoffFilters } from '../types/cutoff';

export const getRoundComparison = async (params: {year: number, round_a: number, round_b: number, college_code?: string, course_code?: string}): Promise<RoundComparisonItem[]> => {
  const { data } = await apiClient.get('/analysis/round-comparison', { params });
  return data;
};

export const getDataQuality = async () => {
  const { data } = await apiClient.get('/analysis/data-quality');
  return data;
};

export const getCategorySummary = async (params?: {year?: number, cap_round_id?: number}) => {
  const { data } = await apiClient.get('/analysis/category-summary', { params });
  return data;
};

export const getFilterOptions = async (): Promise<FilterOptions> => {
  const { data } = await apiClient.get<FilterOptions>('/analysis/filter-options');
  return data;
};

export const getCutoffSummary = async (params?: CutoffFilters): Promise<CutoffSummary> => {
  const { data } = await apiClient.get<CutoffSummary>('/analysis/summary', { params });
  return data;
};

