export const APP_NAME = 'CAP Cutoff Admin Portal';

export const CAP_ROUNDS = [1, 2, 3, 4];

export const STATUS_COLORS: Record<string, string> = {
  'pending': 'info',
  'processing': 'info',
  'completed': 'success',
  'failed': 'error',
  'completed_with_warnings': 'warning',
  'open': 'warning',
  'resolved': 'success',
  'ignored': 'default',
  'warning': 'warning',
  'error': 'error',
  'critical': 'error',
  'successful': 'success'
};
