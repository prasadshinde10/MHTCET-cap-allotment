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
    <div className="flex flex-wrap items-center gap-1.5 py-1">
      <span className="text-[11px] font-medium text-slate-400 mr-1 select-none">Active filters:</span>
      {filters.map((filter) => (
        <span
          key={filter.id}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200/80 transition-colors hover:bg-slate-200/70"
        >
          <span className="text-slate-400 font-normal">{filter.label}:</span>
          <span className="max-w-[200px] truncate font-semibold text-slate-800">{filter.value}</span>
          <button
            type="button"
            onClick={() => onRemove(filter.id)}
            className="text-slate-400 hover:text-slate-700 rounded p-0.5 transition-colors ml-0.5"
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
          className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-md transition-colors ml-1"
        >
          <RotateCcw className="w-2.5 h-2.5" />
          Clear all
        </button>
      )}
    </div>
  );
};

export default FilterChips;
