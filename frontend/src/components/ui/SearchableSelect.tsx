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
          className="block text-xs font-semibold text-[#172B4D] tracking-tight mb-1.5"
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
          'w-full flex items-center justify-between min-h-[36px] px-3 py-1.5 text-left bg-white border rounded-lg text-xs transition-all shadow-subtle',
          isOpen
            ? 'border-[#1769D2] ring-2 ring-[#1769D2]/20'
            : 'border-[#D9E2EC] hover:border-[#1769D2]/60',
          disabled && 'bg-[#F0F4F8] text-[#8292A2] cursor-not-allowed border-[#D9E2EC]'
        )}
      >
        <div className="truncate mr-2 flex items-center gap-1.5">
          {multiple ? (
            values.length === 0 ? (
              <span className="text-[#8292A2] font-normal">{placeholder}</span>
            ) : values.length === 1 ? (
              <span className="text-[#172B4D] font-medium truncate">
                {selectedMultiOptions[0]?.label || values[0]}
              </span>
            ) : (
              <div className="flex items-center gap-1.5 truncate">
                <span className="text-[#172B4D] font-medium truncate">
                  {selectedMultiOptions[0]?.label || values[0]}
                </span>
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-[#EAF3FF] text-[#123B66] border border-[#ADCFFF] flex-shrink-0">
                  +{values.length - 1} more
                </span>
              </div>
            )
          ) : (
            <span className={cn('truncate', !selectedSingleOption && 'text-[#8292A2] font-normal')}>
              {selectedSingleOption ? selectedSingleOption.label : placeholder}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-1 flex-shrink-0">
          {hasSelections && !disabled && (
            <span
              onClick={handleClear}
              className="p-0.5 text-[#5B6B7F] hover:text-[#172B4D] rounded hover:bg-[#F0F4F8] transition-colors"
              title="Clear selection"
            >
              <X className="w-3.5 h-3.5" />
            </span>
          )}
          <ChevronDown
            className={cn(
              'w-3.5 h-3.5 text-[#5B6B7F] transition-transform duration-150',
              isOpen && 'transform rotate-180 text-[#1769D2]'
            )}
          />
        </div>
      </button>

      {/* Dropdown Popover */}
      {isOpen && (
        <div className="absolute z-50 left-0 right-0 mt-1 bg-white border border-[#D9E2EC] rounded-xl shadow-elevated overflow-hidden animate-in fade-in duration-100">
          {/* Search bar inside popover */}
          <div className="p-2 border-b border-[#D9E2EC] bg-[#F7F9FC] flex items-center gap-2">
            <Search className="w-3.5 h-3.5 text-[#5B6B7F] ml-1 flex-shrink-0" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Type to filter..."
              className="w-full bg-transparent text-xs text-[#172B4D] placeholder:text-[#8292A2] focus:outline-none"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="p-1 text-[#5B6B7F] hover:text-[#172B4D] rounded"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Quick action info bar for multi-select */}
          {multiple && (
            <div className="px-3 py-1.5 bg-[#F0F4F8] border-b border-[#D9E2EC] flex items-center justify-between text-[11px] text-[#5B6B7F]">
              <span className="font-medium">
                {values.length === 0 ? 'Select options with checkboxes' : `${values.length} selected`}
              </span>
              {values.length > 0 && (
                <button
                  type="button"
                  onClick={() => onMultiChange?.([])}
                  className="text-[#1769D2] hover:text-[#123B66] font-semibold hover:underline"
                >
                  Clear all
                </button>
              )}
            </div>
          )}

          {/* Options list */}
          <div className="max-h-60 overflow-y-auto py-1 divide-y divide-[#F0F4F8]">
            {filteredOptions.length === 0 ? (
              <div className="px-4 py-3 text-xs text-[#8292A2] text-center">
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
                          ? 'bg-[#EAF3FF] text-[#123B66] font-medium'
                          : 'text-[#172B4D] hover:bg-[#F0F4F8]'
                      )}
                    >
                      <div className="flex items-center min-w-0 pr-2">
                        {/* Checkbox box */}
                        <div
                          className={cn(
                            'w-3.5 h-3.5 rounded border flex items-center justify-center mr-2.5 transition-colors flex-shrink-0',
                            isChecked
                              ? 'bg-[#123B66] border-[#123B66] text-white'
                              : 'border-[#D9E2EC] bg-white'
                          )}
                        >
                          {isChecked && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                        </div>

                        <div className="truncate">
                          <div className="truncate font-medium">{opt.label}</div>
                          {opt.sublabel && (
                            <div className="text-[10px] text-[#5B6B7F] font-normal truncate mt-0.5">
                              {opt.sublabel}
                            </div>
                          )}
                        </div>
                      </div>

                      {isChecked && !isAllOption && (
                        <span className="text-[10px] font-semibold text-[#123B66] bg-[#D5E7FF] px-1.5 py-0.5 rounded flex-shrink-0">
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
                          ? 'bg-[#EAF3FF] text-[#123B66] font-semibold'
                          : 'text-[#172B4D] hover:bg-[#F0F4F8]'
                      )}
                    >
                      <div className="truncate pr-2">
                        <div className="truncate font-medium">{opt.label}</div>
                        {opt.sublabel && (
                          <div className="text-[10px] text-[#5B6B7F] font-normal truncate mt-0.5">
                            {opt.sublabel}
                          </div>
                        )}
                      </div>
                      {isSelected && (
                        <Check className="w-3.5 h-3.5 text-[#1769D2] flex-shrink-0" />
                      )}
                    </button>
                  );
                }
              })
            )}
          </div>
        </div>
      )}

      {helperText && <p className="mt-1 text-[11px] text-[#5B6B7F]">{helperText}</p>}
    </div>
  );
};

export default SearchableSelect;
