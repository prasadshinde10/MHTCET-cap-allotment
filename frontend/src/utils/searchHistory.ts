export interface SearchHistoryFilters {
  course: string;
  collegeType: string;
  category: string;
  reservation: string;
  gender: string;
  district: string;
  year: string;
  round: string;
  percentile?: string;
}

export interface SearchHistoryItem {
  id: string;
  timestamp: string;
  studentNote?: string;
  filters: SearchHistoryFilters;
  totalMatches: number;
}

const STORAGE_KEY = 'mhtcet_admin_search_history';

export const getSearchHistory = (): SearchHistoryItem[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch {
    return [];
  }
};

export const saveSearchHistory = (
  filters: SearchHistoryFilters,
  totalMatches: number,
  studentNote?: string
): SearchHistoryItem => {
  const history = getSearchHistory();
  const newItem: SearchHistoryItem = {
    id: Date.now().toString(),
    timestamp: new Date().toISOString(),
    studentNote: studentNote?.trim() || undefined,
    filters,
    totalMatches,
  };

  // Prepend and keep max 25 items
  const updated = [newItem, ...history.filter((h) => {
    // Avoid exact duplicate consecutive searches
    return JSON.stringify(h.filters) !== JSON.stringify(filters);
  })].slice(0, 25);

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch (e) {
    console.error('Failed to save search history', e);
  }

  return newItem;
};

export const clearSearchHistory = () => {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (e) {
    console.error('Failed to clear search history', e);
  }
};

export const deleteSearchHistoryItem = (id: string): SearchHistoryItem[] => {
  try {
    const history = getSearchHistory().filter((item) => item.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    return history;
  } catch {
    return [];
  }
};
