import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  History, Clock, Search, Trash2, ArrowRight, 
  RotateCcw, BookOpen, MapPin, Sparkles, Building2
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
    if (item.filters.course) params.set('course', item.filters.course);
    if (item.filters.collegeType) params.set('collegeType', item.filters.collegeType);
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
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">Search History</h1>
            <Badge variant="default" className="text-xs">
              {historyItems.length} Record{historyItems.length === 1 ? '' : 's'}
            </Badge>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Review past student counselling queries and reload preferences into the Cutoff Search.
          </p>
        </div>

        {historyItems.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleClearAll}
            className="text-red-600 border-red-200 hover:bg-red-50 flex items-center gap-1.5"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear History
          </Button>
        )}
      </div>

      {/* History List */}
      {historyItems.length === 0 ? (
        <div className="bg-white border border-dashed border-gray-300 rounded-xl p-12 text-center shadow-sm">
          <div className="w-12 h-12 rounded-full bg-gray-100 text-gray-400 flex items-center justify-center mx-auto mb-3">
            <Clock className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-gray-800">No Search History Yet</h3>
          <p className="text-xs text-gray-500 max-w-sm mx-auto mt-1 mb-6">
            Whenever you perform a student consultation on the Cutoff Search page, the query preferences will be recorded here.
          </p>
          <Button
            onClick={() => navigate('/search')}
            className="bg-primary-600 hover:bg-primary-700 text-white"
          >
            Go to Cutoff Search
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {historyItems.map((item) => (
            <div
              key={item.id}
              onClick={() => handleReRun(item)}
              className="bg-white border border-gray-200 hover:border-primary-400 rounded-xl p-4 shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-4 group"
            >
              <div className="space-y-2 flex-1">
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <Clock className="w-3.5 h-3.5" />
                  <span>{formatTimestamp(item.timestamp)}</span>
                  <span>•</span>
                  <span className="text-blue-600 font-medium">
                    {item.totalMatches} College{item.totalMatches === 1 ? '' : 's'} Matched
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-1.5">
                  {item.filters.course ? (
                    <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-100">
                      <BookOpen className="w-3 h-3" />
                      {item.filters.course}
                    </span>
                  ) : (
                    <span className="text-xs text-gray-500 px-2 py-0.5 rounded bg-gray-100">
                      All Branches
                    </span>
                  )}

                  {item.filters.category && (
                    <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded bg-purple-50 text-purple-800 border border-purple-100">
                      Category: {item.filters.category}
                    </span>
                  )}

                  {item.filters.reservation && (
                    <span className="text-xs font-medium px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-100">
                      Quota: {item.filters.reservation}
                    </span>
                  )}

                  {item.filters.district && (
                    <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-100">
                      <MapPin className="w-3 h-3" />
                      {item.filters.district}
                    </span>
                  )}

                  {item.filters.collegeType && (
                    <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded bg-gray-100 text-gray-700">
                      <Building2 className="w-3 h-3" />
                      {item.filters.collegeType}
                    </span>
                  )}

                  {item.filters.gender === 'ladies' && (
                    <span className="text-xs font-medium px-2 py-0.5 rounded bg-pink-50 text-pink-700 border border-pink-100">
                      Ladies Only
                    </span>
                  )}

                  {item.filters.round && (
                    <span className="text-xs font-medium px-2 py-0.5 rounded bg-gray-100 text-gray-600">
                      Round {item.filters.round}
                    </span>
                  )}

                  {item.filters.percentile && (
                    <span className="text-xs font-medium font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-100">
                      Score: ≤ {Number(item.filters.percentile).toFixed(2)}%
                    </span>
                  )}

                  <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
                    Year: {item.filters.year || '2026'}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 self-end md:self-center flex-shrink-0">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleReRun(item)}
                  className="group-hover:bg-primary-50 group-hover:text-primary-700 group-hover:border-primary-300 text-xs flex items-center gap-1"
                >
                  Load Preferences
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>

                <button
                  type="button"
                  onClick={(e) => handleDeleteItem(item.id, e)}
                  className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title="Delete this record"
                >
                  <Trash2 className="w-4 h-4" />
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
