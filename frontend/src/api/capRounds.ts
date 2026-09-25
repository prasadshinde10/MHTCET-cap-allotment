import apiClient from './client';

export interface CapRound {
  id: number;
  year: number;
  round_number: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export const getCapRounds = async () => {
  const { data } = await apiClient.get<CapRound[]>('/cap-rounds');
  return data;
};

export const getCapRound = async (id: number) => {
  const { data } = await apiClient.get<CapRound>(`/cap-rounds/${id}`);
  return data;
};

export const getCapRoundStats = async (id: number) => {
  const { data } = await apiClient.get(`/cap-rounds/${id}/stats`);
  return data;
};
