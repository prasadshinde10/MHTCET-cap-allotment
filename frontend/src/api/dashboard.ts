import { apiClient } from './client';
import { DashboardStats } from '../types/dashboard';

export const dashboardApi = {
  getDashboardStats: async (): Promise<DashboardStats> => {
    const { data } = await apiClient.get<DashboardStats>('/dashboard/stats');
    return data;
  },
};
