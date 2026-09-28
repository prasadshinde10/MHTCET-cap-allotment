import React, { useState, useRef, useEffect, useMemo } from 'react';
import { ChevronDown, Search, X, Check } from 'lucide-react';
import { cn } from '../../utils/utils';

export interface SearchableOption {
  value: string;
  label: string;
  sublabel?: string;
}

interface SearchableSelectProps {
  label?: string;
  placeholder?: string;
  options: SearchableOption[];
  // Single-select props
  value?: string;
  onChange?: (value: string) => void;
  // Multi-select props
  multiple?: boolean;
  values?: string[];
  onMultiChange?: (values: string[]) => void;
  disabled?: boolean;
  className?: string;
  id?: string;
  helperText?: string;
}

export const SearchableSelect: React.FC<SearchableSelectProps> = ({
  label,
  placeholder = 'Select option...',
  options,
  value = '',
  onChange,
  multiple = false,
  values = [],
  onMultiChange,
  disabled = false,
  className,
  id,
  helperText,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 50);
    } else {
      setSearchQuery('');
    }
  }, [isOpen]);

  const filteredOptions = useMemo(() => {
    if (!searchQuery.trim()) return options;
    const q = searchQuery.toLowerCase();
    return options.filter((opt) => {
      return (
        opt.label.toLowerCase().includes(q) ||
        (opt.sublabel && opt.sublabel.toLowerCase().includes(q)) ||
        opt.value.toLowerCase().includes(q)
      );
    });
  }, [options, searchQuery]);

  // Labels for multi-select
  const selectedMultiOptions = useMemo(() => {
    if (!multiple) return [];
    return options.filter((opt) => values.includes(opt.value));
  }, [options, values, multiple]);

  const selectedSingleOption = useMemo(() => {
    if (multiple) return undefined;
    return options.find((opt) => opt.value === value);
  }, [options, value, multiple]);

  const handleSingleSelect = (val: string) => {
    onChange?.(val);
    setIsOpen(false);
  };

  const handleToggleMulti = (val: string) => {
    if (!onMultiChange) return;
    if (!val) {
      // Clicked "All" option -> clear specific selections
      onMultiChange([]);
      return;
    }

    if (values.includes(val)) {
      onMultiChange(values.filter((v) => v !== val));
    } else {
      onMultiChange([...values, val]);
    }
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (multiple) {
      onMultiChange?.([]);
    } else {
      onChange?.('');
    }
  };

  const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
  const hasSelections = multiple ? values.length > 0 : Boolean(value);

  return (
    <div className={cn('w-full relative', className)} ref={containerRef}>
      {label && (
        <label
          htmlFor={selectId}
          className="block text-xs font-semibold text-slate-700 tracking-tight mb-1.5"
        >
          {label}
        </label>
      )}

      {/* Button / Trigger */}
      <button
        type="button"
        id={selectId}
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'w-full flex items-center justify-between min-h-[36px] px-3 py-1.5 text-left bg-white border rounded-lg text-xs transition-all shadow-sm',
          isOpen
            ? 'border-blue-600 ring-2 ring-blue-600/15'
            : 'border-slate-300 hover:border-slate-400',
          disabled && 'bg-slate-50 text-slate-400 cursor-not-allowed border-slate-200'
        )}
      >
        <div className="truncate mr-2 flex items-center gap-1.5">
          {multiple ? (
            values.length === 0 ? (
              <span className="text-slate-400 font-normal">{placeholder}</span>
            ) : values.length === 1 ? (
              <span className="text-slate-900 font-medium truncate">
                {selectedMultiOptions[0]?.label || values[0]}
              </span>
            ) : (
              <div className="flex items-center gap-1.5 truncate">
                <span className="text-slate-900 font-medium truncate">
                  {selectedMultiOptions[0]?.label || values[0]}
                </span>
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200/60 flex-shrink-0">
                  +{values.length - 1} more
                </span>
              </div>
            )
          ) : (
            <span className={cn('truncate', !selectedSingleOption && 'text-slate-400 font-normal')}>
              {selectedSingleOption ? selectedSingleOption.label : placeholder}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-1 flex-shrink-0">
          {hasSelections && !disabled && (
            <span
              onClick={handleClear}
              className="p-0.5 text-slate-400 hover:text-slate-600 rounded hover:bg-slate-100 transition-colors"
              title="Clear selection"
            >
              <X className="w-3.5 h-3.5" />
            </span>
          )}
          <ChevronDown
            className={cn(
              'w-3.5 h-3.5 text-slate-400 transition-transform duration-150',
              isOpen && 'transform rotate-180 text-blue-600'
            )}
          />
        </div>
      </button>

      {/* Dropdown Popover */}
      {isOpen && (
        <div className="absolute z-50 left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden animate-in fade-in duration-100">
          {/* Search bar inside popover */}
          <div className="p-2 border-b border-slate-100 bg-slate-50/60 flex items-center gap-2">
            <Search className="w-3.5 h-3.5 text-slate-400 ml-1 flex-shrink-0" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Type to filter..."
              className="w-full bg-transparent text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="p-1 text-slate-400 hover:text-slate-600 rounded"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Quick action info bar for multi-select */}
          {multiple && (
            <div className="px-3 py-1.5 bg-slate-50/80 border-b border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
              <span className="font-medium">
                {values.length === 0 ? 'Select options with checkboxes' : `${values.length} selected`}
              </span>
              {values.length > 0 && (
                <button
                  type="button"
                  onClick={() => onMultiChange?.([])}
                  className="text-blue-600 hover:text-blue-700 font-semibold hover:underline"
                >
                  Clear all
                </button>
              )}
            </div>
          )}

          {/* Options list */}
          <div className="max-h-60 overflow-y-auto py-1 divide-y divide-slate-50">
            {filteredOptions.length === 0 ? (
              <div className="px-4 py-3 text-xs text-slate-400 text-center">
                No matching options found
              </div>
            ) : (
              filteredOptions.map((opt) => {
                if (multiple) {
                  // Multi-select option with checkbox
                  const isAllOption = opt.value === '';
                  const isChecked = isAllOption ? values.length === 0 : values.includes(opt.value);

                  return (
                    <button
                      key={opt.value || '__all__'}
                      type="button"
                      onClick={() => handleToggleMulti(opt.value)}
                      className={cn(
                        'w-full text-left px-3 py-2 text-xs flex items-center justify-between transition-colors',
                        isChecked
                          ? 'bg-blue-50/60 text-blue-900 font-medium'
                          : 'text-slate-700 hover:bg-slate-50'
                      )}
                    >
                      <div className="flex items-center min-w-0 pr-2">
                        {/* Checkbox box */}
                        <div
                          className={cn(
                            'w-3.5 h-3.5 rounded border flex items-center justify-center mr-2.5 transition-colors flex-shrink-0',
                            isChecked
                              ? 'bg-blue-600 border-blue-600 text-white'
                              : 'border-slate-300 bg-white'
                          )}
                        >
                          {isChecked && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                        </div>

                        <div className="truncate">
                          <div className="truncate font-medium">{opt.label}</div>
                          {opt.sublabel && (
                            <div className="text-[10px] text-slate-400 font-normal truncate mt-0.5">
                              {opt.sublabel}
                            </div>
                          )}
                        </div>
                      </div>

                      {isChecked && !isAllOption && (
                        <span className="text-[10px] font-semibold text-blue-600 bg-blue-100/70 px-1.5 py-0.5 rounded flex-shrink-0">
                          Selected
                        </span>
                      )}
                    </button>
                  );
                } else {
                  // Single-select option
                  const isSelected = opt.value === value;
                  return (
                    <button
                      key={opt.value || '__all__'}
                      type="button"
                      onClick={() => handleSingleSelect(opt.value)}
                      className={cn(
                        'w-full text-left px-3 py-2 text-xs flex items-center justify-between transition-colors',
                        isSelected
                          ? 'bg-blue-50 text-blue-900 font-semibold'
                          : 'text-slate-700 hover:bg-slate-50'
                      )}
                    >
                      <div className="truncate pr-2">
                        <div className="truncate font-medium">{opt.label}</div>
                        {opt.sublabel && (
                          <div className="text-[10px] text-slate-400 font-normal truncate mt-0.5">
                            {opt.sublabel}
                          </div>
                        )}
                      </div>
                      {isSelected && (
                        <Check className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />
                      )}
                    </button>
                  );
                }
              })
            )}
          </div>
        </div>
      )}

      {helperText && <p className="mt-1 text-[11px] text-slate-500">{helperText}</p>}
    </div>
  );
};

export default SearchableSelect;
