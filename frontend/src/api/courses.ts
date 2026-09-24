import apiClient from './client';
import { Course } from '../types/course';
import { PaginatedResponse } from '../types/common';

export type { Course };

export const getCourses = async (params?: {
  page?: number;
  page_size?: number;
  search?: string;
  college_id?: number;
}) => {
  const { data } = await apiClient.get<PaginatedResponse<Course>>('/courses', { params });
  return data;
};

export const getCourse = async (id: number) => {
  const { data } = await apiClient.get<Course>(`/courses/${id}`);
  return data;
};

export const updateCourse = async (id: number, updateData: { course_name: string }) => {
  const { data } = await apiClient.put<Course>(`/courses/${id}`, updateData);
  return data;
};
