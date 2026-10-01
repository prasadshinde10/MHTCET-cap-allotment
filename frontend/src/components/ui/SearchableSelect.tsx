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
          className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5"
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
          'w-full flex items-center justify-between min-h-[42px] px-3.5 py-2 text-left bg-white border rounded-lg text-sm transition-colors shadow-sm',
          isOpen
            ? 'border-primary-500 ring-2 ring-primary-100'
            : 'border-gray-300 hover:border-gray-400',
          disabled && 'bg-gray-100 text-gray-400 cursor-not-allowed border-gray-200'
        )}
      >
        <div className="truncate mr-2 flex items-center gap-1.5">
          {multiple ? (
            values.length === 0 ? (
              <span className="text-gray-400 font-normal">{placeholder}</span>
            ) : values.length === 1 ? (
              <span className="text-gray-900 font-medium truncate">
                {selectedMultiOptions[0]?.label || values[0]}
              </span>
            ) : (
              <div className="flex items-center gap-1.5 truncate">
                <span className="text-gray-900 font-medium truncate">
                  {selectedMultiOptions[0]?.label || values[0]}
                </span>
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-semibold bg-primary-50 text-primary-700 border border-primary-100 flex-shrink-0">
                  +{values.length - 1} more
                </span>
              </div>
            )
          ) : (
            <span className={cn('truncate', !selectedSingleOption && 'text-gray-400 font-normal')}>
              {selectedSingleOption ? selectedSingleOption.label : placeholder}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-1 flex-shrink-0">
          {hasSelections && !disabled && (
            <span
              onClick={handleClear}
              className="p-0.5 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors"
              title="Clear selection"
            >
              <X className="w-3.5 h-3.5" />
            </span>
          )}
          <ChevronDown
            className={cn(
              'w-4 h-4 text-gray-400 transition-transform duration-200',
              isOpen && 'transform rotate-180 text-primary-600'
            )}
          />
        </div>
      </button>

      {/* Dropdown Popover */}
      {isOpen && (
        <div className="absolute z-50 left-0 right-0 mt-1.5 bg-white border border-gray-200 rounded-lg shadow-xl overflow-hidden animate-in fade-in slide-in-from-top-1 duration-150">
          {/* Search bar inside popover */}
          <div className="p-2.5 border-b border-gray-100 bg-gray-50 flex items-center gap-2">
            <Search className="w-4 h-4 text-gray-400 ml-1 flex-shrink-0" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Type to filter..."
              className="w-full bg-transparent text-sm text-gray-800 placeholder-gray-400 focus:outline-none"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="p-1 text-gray-400 hover:text-gray-600 rounded-full"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Quick action info bar for multi-select */}
          {multiple && (
            <div className="px-3 py-1.5 bg-gray-50 border-b border-gray-100 flex items-center justify-between text-xs text-gray-500">
              <span className="font-semibold text-gray-700">
                {values.length === 0 ? 'Select options with checkboxes' : `${values.length} Selected`}
              </span>
              {values.length > 0 && (
                <button
                  type="button"
                  onClick={() => onMultiChange?.([])}
                  className="text-red-600 hover:text-red-700 font-medium hover:underline text-xs"
                >
                  Uncheck All ({values.length})
                </button>
              )}
            </div>
          )}

          {/* Quick-uncheck pills inside popover */}
          {multiple && selectedMultiOptions.length > 0 && (
            <div className="p-2 bg-indigo-50/50 border-b border-indigo-100 max-h-24 overflow-y-auto">
              <div className="text-[10px] font-bold text-indigo-900 uppercase tracking-wider mb-1 px-0.5">
                Active Selections (Click × to uncheck):
              </div>
              <div className="flex flex-wrap gap-1">
                {selectedMultiOptions.map((opt) => (
                  <span
                    key={opt.value}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-white text-indigo-950 border border-indigo-200 shadow-2xs"
                  >
                    <span className="truncate max-w-[200px]" title={opt.label}>{opt.label}</span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleToggleMulti(opt.value);
                      }}
                      className="text-gray-400 hover:text-red-600 p-0.5 rounded-full"
                      title={`Uncheck ${opt.label}`}
                    >
                      <X className="w-3 h-3 stroke-[2.5]" />
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Options list */}
          <div className="max-h-60 overflow-y-auto py-1 divide-y divide-gray-50">
            {filteredOptions.length === 0 ? (
              <div className="px-4 py-3 text-xs text-gray-500 text-center">
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
                        'w-full text-left px-3.5 py-2.5 text-xs sm:text-sm flex items-center justify-between transition-colors',
                        isChecked
                          ? 'bg-primary-50/60 text-primary-900 font-medium'
                          : 'text-gray-700 hover:bg-gray-50'
                      )}
                    >
                      <div className="flex items-center min-w-0 pr-2">
                        {/* Checkbox box */}
                        <div
                          className={cn(
                            'w-4 h-4 rounded border flex items-center justify-center mr-2.5 transition-colors flex-shrink-0',
                            isChecked
                              ? 'bg-primary-600 border-primary-600 text-white shadow-xs'
                              : 'border-gray-300 bg-white'
                          )}
                        >
                          {isChecked && <Check className="w-3 h-3 stroke-[3]" />}
                        </div>

                        <div className="truncate">
                          <div className="truncate">{opt.label}</div>
                          {opt.sublabel && (
                            <div className="text-[11px] text-gray-400 font-normal truncate mt-0.5">
                              {opt.sublabel}
                            </div>
                          )}
                        </div>
                      </div>

                      {isChecked && !isAllOption && (
                        <span className="text-[11px] font-semibold text-primary-600 bg-primary-100/60 px-1.5 py-0.5 rounded flex-shrink-0">
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
                        'w-full text-left px-3.5 py-2.5 text-xs sm:text-sm flex items-center justify-between transition-colors',
                        isSelected
                          ? 'bg-primary-50 text-primary-900 font-semibold'
                          : 'text-gray-700 hover:bg-gray-50'
                      )}
                    >
                      <div className="truncate pr-2">
                        <div className="truncate">{opt.label}</div>
                        {opt.sublabel && (
                          <div className="text-[11px] text-gray-400 font-normal truncate mt-0.5">
                            {opt.sublabel}
                          </div>
                        )}
                      </div>
                      {isSelected && (
                        <Check className="w-4 h-4 text-primary-600 flex-shrink-0" />
                      )}
                    </button>
                  );
                }
              })
            )}
          </div>
        </div>
      )}

      {/* Selected badges for multi-select (visible directly below trigger with uncheck button) */}
      {multiple && values.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {selectedMultiOptions.map((opt) => (
            <span
              key={opt.value}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-800 border border-slate-300 shadow-2xs hover:bg-slate-200/70 transition-colors"
            >
              <span className="truncate max-w-[280px]" title={opt.label}>
                {opt.label}
              </span>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleToggleMulti(opt.value);
                }}
                className="text-slate-400 hover:text-red-600 rounded-full p-0.5 hover:bg-white/80 transition-colors"
                title={`Remove / Uncheck ${opt.label}`}
              >
                <X className="w-3.5 h-3.5 stroke-[2.5]" />
              </button>
            </span>
          ))}
        </div>
      )}

      {helperText && <p className="mt-1 text-xs text-gray-500">{helperText}</p>}
    </div>
  );
};

export default SearchableSelect;
