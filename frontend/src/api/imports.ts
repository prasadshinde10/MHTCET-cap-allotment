import apiClient from './client';
import {
  UploadResponse,
  ImportBatch,
  ImportBatchDetail,
  PaginatedResponse,
  StagingCutoff,
  CommitResponse
} from '../types/import';


export interface ProcessBatchResponse {
  status: string;
  pages_processed: number;
  records_created: number;
  colleges_found?: number;
  courses_found?: number;
  warnings?: number;
  errors?: number;
}

export interface DbStatus {
  total_cutoffs: number;
  total_colleges: number;
  total_courses: number;
  total_batches: number;
}

export interface ResetDbResponse {
  success: boolean;
  message: string;
  backup_file?: string;
}

export const uploadPdf = async (file: File, year: number, roundNumber: number): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('year', year.toString());
  formData.append('round_number', roundNumber.toString());

  const response = await apiClient.post<UploadResponse>(`/imports/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const processBatch = async (batchId: number): Promise<ProcessBatchResponse> => {
  const response = await apiClient.post<ProcessBatchResponse>(`/imports/${batchId}/process`);
  return response.data;
};

export const getDbStatus = async (): Promise<DbStatus> => {
  const response = await apiClient.get<DbStatus>('/imports/db-status');
  return response.data;
};

export const resetDatabase = async (): Promise<ResetDbResponse> => {
  const response = await apiClient.post<ResetDbResponse>('/imports/reset-database');
  return response.data;
};

export const getImportBatches = async (params?: {
  page?: number;
  page_size?: number;
  status?: string;
  year?: number;
  cap_round_id?: number;
}): Promise<PaginatedResponse<ImportBatch>> => {
  const response = await apiClient.get<PaginatedResponse<ImportBatch>>('/imports', { params });
  return response.data;
};

export const getImportBatchDetail = async (batchId: number): Promise<ImportBatchDetail> => {
  const response = await apiClient.get<ImportBatchDetail>(`/imports/${batchId}`);
  return response.data;
};

export const getStagingRecords = async (
  batchId: number,
  params?: { page?: number; page_size?: number }
): Promise<PaginatedResponse<StagingCutoff>> => {
  const response = await apiClient.get<PaginatedResponse<StagingCutoff>>(`/imports/${batchId}/staging`, { params });
  return response.data;
};

export const commitBatch = async (batchId: number): Promise<CommitResponse> => {
  const response = await apiClient.post<CommitResponse>(`/imports/${batchId}/commit`);
  return response.data;
};

export const deleteBatch = async (batchId: number): Promise<{ message: string }> => {
  const response = await apiClient.delete<{ message: string }>(`/imports/${batchId}`);
  return response.data;
};
