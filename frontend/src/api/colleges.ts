import apiClient from './client';
import { College } from '../types/college';
import { PaginatedResponse } from '../types/common';

export type { College };

export const getColleges = async (params?: {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  college_type?: string;
  funding_type?: string;
}) => {
  const { data } = await apiClient.get<PaginatedResponse<College>>('/colleges', { params });
  return data;
};

export const getCollege = async (id: number) => {
  const { data } = await apiClient.get<College>(`/colleges/${id}`);
  return data;
};

export const updateCollege = async (id: number, updateData: Partial<College>) => {
  const { data } = await apiClient.put<College>(`/colleges/${id}`, updateData);
  return data;
};

export const getCollegeCourses = async (collegeId: number) => {
  const { data } = await apiClient.get(`/colleges/${collegeId}/courses`);
  return data;
};
