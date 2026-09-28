import React, { forwardRef } from 'react';
import { cn } from '../../utils/utils';
import { ChevronDown } from 'lucide-react';

export interface SelectOption {
  value: string | number;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helperText?: string;
  options: SelectOption[];
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, helperText, options, id, ...props }, ref) => {
    const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={selectId}
            className="block text-xs font-semibold text-[#172B4D] tracking-tight mb-1.5"
          >
            {label}
          </label>
        )}
        <div className="relative">
          <select
            id={selectId}
            ref={ref}
            className={cn(
              'block w-full h-9 appearance-none rounded-lg border border-[#D9E2EC] bg-white px-3 pr-8 py-1.5 text-xs text-[#172B4D] shadow-subtle transition-all focus:border-[#1769D2] focus:outline-none focus:ring-2 focus:ring-[#1769D2]/20 disabled:cursor-not-allowed disabled:bg-[#F0F4F8] disabled:text-[#8292A2]',
              error && 'border-[#C53030] text-[#C53030] focus:border-[#C53030] focus:ring-[#C53030]/20',
              className
            )}
            {...props}
          >
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2.5 text-[#5B6B7F]">
            <ChevronDown className="w-3.5 h-3.5" />
          </div>
        </div>
        {helperText && !error && (
          <p className="mt-1 text-[11px] text-[#5B6B7F]">{helperText}</p>
        )}
        {error && (
          <p className="mt-1 text-xs text-[#C53030] font-medium">{error}</p>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';

export default Select;
