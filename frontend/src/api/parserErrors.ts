import apiClient from './client';
import { PaginatedResponse } from '../types/common';

export interface ParserError {
  id: number;
  import_batch_id: number;
  source_page?: number;
  error_type: string;
  severity: string;
  raw_text?: string | null;
  error_message: string;
  college_code?: string;
  course_code?: string;
  status: string;
  context?: any;
  created_at: string;
}

export const getParserErrors = async (params?: {
  page?: number;
  page_size?: number;
  import_batch_id?: number;
  severity?: string;
  error_type?: string;
  status?: string;
}) => {
  const { data } = await apiClient.get<PaginatedResponse<ParserError>>('/parser-errors', { params });
  return data;
};

export const getParserError = async (id: number) => {
  const { data } = await apiClient.get<ParserError>(`/parser-errors/${id}`);
  return data;
};

export const updateParserError = async (id: number, updateData: { status: string; resolution_notes?: string }) => {
  const { data } = await apiClient.put<ParserError>(`/parser-errors/${id}`, updateData);
  return data;
};

export const getParserErrorSummary = async () => {
  const { data } = await apiClient.get('/parser-errors/summary');
  return data;
};
