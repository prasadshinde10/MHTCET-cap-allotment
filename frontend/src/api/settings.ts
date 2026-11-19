import apiClient from './client';

export interface UpdateCheckResult {
  current_version: string;
  latest_version: string;
  update_available: boolean;
  release_title?: string | null;
  release_notes?: string | null;
  published_at?: string | null;
  release_url?: string | null;
  download_url?: string | null;
  asset_name?: string | null;
  asset_size_mb?: number | null;
  cached?: boolean;
  checked_at?: number | null;
  error?: string | null;
}

export const getSystemSettings = async () => {
  const { data } = await apiClient.get('/settings');
  return data;
};

export const checkForUpdates = async (forceRefresh: boolean = false): Promise<UpdateCheckResult> => {
  const { data } = await apiClient.get<UpdateCheckResult>('/settings/check-update', {
    params: { force_refresh: forceRefresh },
  });
  return data;
};

export interface UpdateProgressResult {
  status: 'idle' | 'downloading' | 'extracting' | 'ready' | 'failed';
  progress_percent: number;
  downloaded_bytes: number;
  total_bytes: number;
  downloaded_mb: number;
  total_mb: number;
  message: string;
  target_version: string;
  error?: string | null;
}

export const getUpdateProgress = async (): Promise<UpdateProgressResult> => {
  const { data } = await apiClient.get<UpdateProgressResult>('/settings/update-progress');
  return data;
};

export const startInPlaceUpdate = async () => {
  const { data } = await apiClient.post('/settings/apply-update');
  return data;
};

export const restartAndApplyUpdate = async () => {
  const { data } = await apiClient.post('/settings/restart-and-apply');
  return data;
};

