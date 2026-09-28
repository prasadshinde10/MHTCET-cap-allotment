import React, { forwardRef } from 'react';
import { cn } from '../../utils/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className, id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="w-full">
        {label && (
          <label htmlFor={inputId} className="block text-xs font-semibold text-[#172B4D] tracking-tight mb-1.5">
            {label}
          </label>
        )}
        <input
          id={inputId}
          ref={ref}
          className={cn(
            "block w-full h-9 rounded-lg border border-[#D9E2EC] bg-white px-3 py-1.5 text-xs text-[#172B4D] placeholder:text-[#8292A2] shadow-subtle transition-all focus:border-[#1769D2] focus:outline-none focus:ring-2 focus:ring-[#1769D2]/20 disabled:bg-[#F0F4F8] disabled:text-[#8292A2] disabled:cursor-not-allowed",
            error && "border-[#C53030] text-[#C53030] focus:border-[#C53030] focus:ring-[#C53030]/20",
            className
          )}
          {...props}
        />
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
Input.displayName = 'Input';

export default Input;
