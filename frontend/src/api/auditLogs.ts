import apiClient from './client';
import { PaginatedResponse } from '../types/common';

export interface AuditLog {
  id: number;
  action: string;
  entity_type: string;
  entity_id: number | null;
  details: any;
  ip_address: string | null;
  created_at: string;
}

export const getAuditLogs = async (params?: {
  page?: number;
  page_size?: number;
  action?: string;
  entity_type?: string;
  date_from?: string;
  date_to?: string;
}) => {
  const { data } = await apiClient.get<PaginatedResponse<AuditLog>>('/audit-logs', { params });
  return data;
};
