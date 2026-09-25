import apiClient from './client';

export const getSystemSettings = async () => {
  const { data } = await apiClient.get('/settings');
  return data;
};
