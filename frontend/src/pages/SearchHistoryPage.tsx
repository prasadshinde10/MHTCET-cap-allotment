import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Clock, Search, Trash2, ArrowRight, 
  BookOpen, MapPin, Building2
} from 'lucide-react';
import { 
  getSearchHistory, 
  clearSearchHistory, 
  deleteSearchHistoryItem, 
  SearchHistoryItem 
} from '../utils/searchHistory';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import toast from 'react-hot-toast';

export const SearchHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [historyItems, setHistoryItems] = useState<SearchHistoryItem[]>([]);

  useEffect(() => {
    setHistoryItems(getSearchHistory());
  }, []);

  const handleClearAll = () => {
    if (window.confirm('Are you sure you want to clear all consultation search history?')) {
      clearSearchHistory();
      setHistoryItems([]);
      toast.success('Search history cleared');
    }
  };

  const handleDeleteItem = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updated = deleteSearchHistoryItem(id);
    setHistoryItems(updated);
    toast.success('Search record removed');
  };

  const handleReRun = (item: SearchHistoryItem) => {
    const params = new URLSearchParams();
    if (item.filters.college) params.set('college', item.filters.college);
    if (item.filters.course) params.set('course', item.filters.course);
    if (item.filters.collegeType) params.set('collegeType', item.filters.collegeType);
    if (item.filters.autonomyStatus) params.set('autonomy', item.filters.autonomyStatus);
    if (item.filters.category) params.set('category', item.filters.category);
    if (item.filters.reservation) params.set('reservation', item.filters.reservation);
    if (item.filters.gender) params.set('gender', item.filters.gender);
    if (item.filters.district) params.set('district', item.filters.district);
    if (item.filters.year) params.set('year', item.filters.year);
    if (item.filters.round) params.set('round', item.filters.round);
    if (item.filters.percentile) params.set('percentile', item.filters.percentile);

    navigate(`/search?${params.toString()}`);
  };

  const formatTimestamp = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-4 pb-12">
      {/* Header */}
      <div className="bg-white border border-slate-200/90 rounded-xl p-4 sm:p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold text-slate-900 tracking-tight">Search History</h1>
            <Badge variant="default">
              {historyItems.length} Record{historyItems.length === 1 ? '' : 's'}
            </Badge>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Review past student counselling queries and reload preferences into the Cutoff Search.
          </p>
        </div>

        {historyItems.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleClearAll}
            className="text-rose-600 border-rose-200 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-300"
          >
            <Trash2 className="w-3.5 h-3.5 mr-1" />
            Clear History
          </Button>
        )}
      </div>

      {/* History List */}
      {historyItems.length === 0 ? (
        <div className="bg-white border border-dashed border-slate-200 rounded-xl p-10 text-center shadow-xs">
          <div className="w-10 h-10 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-2.5">
            <Clock className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-semibold text-slate-800">No Search History Yet</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-4">
            Whenever you perform a student consultation on the Cutoff Search page, the query preferences will be recorded here.
          </p>
          <Button
            onClick={() => navigate('/search')}
            size="sm"
            className="text-xs"
          >
            <Search className="w-3.5 h-3.5 mr-1.5" />
            Go to Cutoff Search
          </Button>
        </div>
      ) : (
        <div className="space-y-2.5">
          {historyItems.map((item) => (
            <div
              key={item.id}
              onClick={() => handleReRun(item)}
              className="bg-white border border-slate-200/90 hover:border-blue-400/80 rounded-xl p-3.5 sm:p-4 shadow-xs hover:shadow-sm transition-all cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-3 group"
            >
              <div className="space-y-2 flex-1 min-w-0">
                <div className="flex items-center gap-2 text-[11px] text-slate-400">
                  <Clock className="w-3 h-3" />
                  <span>{formatTimestamp(item.timestamp)}</span>
                  <span>•</span>
                  <span className="text-blue-600 font-semibold">
                    {item.totalMatches} Offering{item.totalMatches === 1 ? '' : 's'} Matched
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-1.5">
                  {item.filters.college && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
                      <Building2 className="w-3 h-3 text-slate-400" />
                      College: {item.filters.college}
                    </span>
                  )}

                  {item.filters.course ? (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md bg-blue-50 text-blue-800 border border-blue-200/70">
                      <BookOpen className="w-3 h-3 text-blue-500" />
                      {item.filters.course}
                    </span>
                  ) : (
                    <span className="text-[11px] text-slate-500 px-2 py-0.5 rounded-md bg-slate-100">
                      All Branches
                    </span>
                  )}

                  {item.filters.category && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-purple-50 text-purple-700 border border-purple-200/60">
                      Category: {item.filters.category}
                    </span>
                  )}

                  {item.filters.reservation && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-200/60">
                      Quota: {item.filters.reservation}
                    </span>
                  )}

                  {item.filters.district && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                      <MapPin className="w-3 h-3 text-emerald-500" />
                      {item.filters.district}
                    </span>
                  )}

                  {item.filters.collegeType && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
                      {item.filters.collegeType}
                    </span>
                  )}

                  {item.filters.autonomyStatus && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200/60">
                      {item.filters.autonomyStatus}
                    </span>
                  )}

                  {item.filters.gender === 'ladies' && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-rose-50 text-rose-700 border border-rose-200/60">
                      Ladies Only
                    </span>
                  )}

                  {item.filters.round && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 border border-slate-200">
                      Round {item.filters.round}
                    </span>
                  )}

                  {item.filters.percentile && (
                    <span className="text-[11px] font-medium font-mono px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                      Score: ≤ {Number(item.filters.percentile).toFixed(2)}%
                    </span>
                  )}

                  <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
                    Year: {item.filters.year || '2026'}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 self-end md:self-center flex-shrink-0">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleReRun(item)}
                  className="group-hover:bg-blue-50 group-hover:text-blue-700 group-hover:border-blue-300 text-xs"
                >
                  Load Preferences
                  <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Button>

                <button
                  type="button"
                  onClick={(e) => handleDeleteItem(item.id, e)}
                  className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                  title="Delete record"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SearchHistoryPage;
