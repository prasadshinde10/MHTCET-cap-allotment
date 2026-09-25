import React from 'react';
import { X, RotateCcw } from 'lucide-react';

export interface ActiveFilter {
  id: string;
  label: string;
  value: string;
}

interface FilterChipsProps {
  filters: ActiveFilter[];
  onRemove: (id: string) => void;
  onClearAll: () => void;
}

export const FilterChips: React.FC<FilterChipsProps> = ({
  filters,
  onRemove,
  onClearAll,
}) => {
  if (filters.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 pt-1 pb-2">
      <span className="text-xs font-medium text-gray-500 mr-1">Active filters:</span>
      {filters.map((filter) => (
        <span
          key={filter.id}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-800 border border-blue-200"
        >
          <span className="font-semibold text-blue-900">{filter.label}:</span>
          <span className="max-w-[200px] truncate">{filter.value}</span>
          <button
            type="button"
            onClick={() => onRemove(filter.id)}
            className="text-blue-600 hover:text-blue-900 hover:bg-blue-100 rounded p-0.5 transition-colors"
            title={`Remove ${filter.label}`}
          >
            <X className="w-3 h-3" />
          </button>
        </span>
      ))}
      {filters.length > 1 && (
        <button
          type="button"
          onClick={onClearAll}
          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
        >
          <RotateCcw className="w-3 h-3" />
          Clear all
        </button>
      )}
    </div>
  );
};

export default FilterChips;
