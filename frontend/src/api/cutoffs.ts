import apiClient from './client';
import { Cutoff, CutoffFilters } from '../types/cutoff';
import { PaginatedResponse } from '../types/common';

export type { Cutoff, CutoffFilters };

export const getCutoffs = async (params?: CutoffFilters) => {
  const { data } = await apiClient.get<PaginatedResponse<Cutoff>>('/cutoffs', { params });
  return data;
};

export const getCutoff = async (id: number) => {
  const { data } = await apiClient.get<Cutoff>(`/cutoffs/${id}`);
  return data;
};

export const exportCutoffs = async (params?: CutoffFilters) => {
  const response = await apiClient.get('/cutoffs/export', {
    params,
    responseType: 'blob',
  });
  return response.data;
};

