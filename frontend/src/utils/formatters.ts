export const formatDate = (dateString: string): string => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

export const formatNumber = (n: number | undefined | null): string => {
  if (n === undefined || n === null) return '0';
  return new Intl.NumberFormat('en-IN').format(n);
};

export const formatPercentile = (p: number | undefined | null): string => {
  if (p === undefined || p === null) return '0.0000000';
  return p.toFixed(7);
};
