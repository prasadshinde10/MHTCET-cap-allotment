import { apiClient } from './client';
import { AdminUser, LoginCredentials, LoginResponse } from '../types/auth';
import { MessageResponse } from '../types/common';

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<LoginResponse> => {
    const { data } = await apiClient.post<LoginResponse>('/auth/login', credentials);
    return data;
  },

  logout: async (): Promise<MessageResponse> => {
    const { data } = await apiClient.post<MessageResponse>('/auth/logout');
    return data;
  },

  getMe: async (): Promise<AdminUser> => {
    const { data } = await apiClient.get<AdminUser>('/auth/me');
    return data;
  },
};
