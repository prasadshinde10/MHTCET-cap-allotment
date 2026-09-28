import React from 'react';
import { cn } from '../../utils/utils';
import { Spinner } from './Spinner';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  className,
  disabled,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-150 select-none focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none active:scale-[0.99]';
  
  const variants = {
    primary: 'bg-[#123B66] text-white hover:bg-[#0B2545] active:bg-[#081D36] shadow-subtle border border-[#123B66]/20 focus-visible:ring-[#1769D2]/30',
    secondary: 'bg-white text-[#172B4D] border border-[#D9E2EC] hover:bg-[#F0F4F8] hover:text-[#0B2545] active:bg-[#D9E2EC]/50 shadow-subtle focus-visible:ring-[#1769D2]/20',
    outline: 'bg-transparent text-[#172B4D] border border-[#D9E2EC] hover:bg-[#F0F4F8] hover:text-[#0B2545] active:bg-[#D9E2EC]/40 focus-visible:ring-[#1769D2]/20',
    danger: 'bg-[#C53030] text-white hover:bg-[#9B2C2C] active:bg-[#742A2A] shadow-subtle focus-visible:ring-[#C53030]/30',
    ghost: 'bg-transparent text-[#5B6B7F] hover:bg-[#F0F4F8] hover:text-[#172B4D] active:bg-[#D9E2EC]/50 focus-visible:ring-[#1769D2]/20',
  };
  
  const sizes = {
    sm: 'px-2.5 py-1.5 text-xs gap-1.5 h-8',
    md: 'px-3.5 py-2 text-xs font-semibold gap-2 h-9',
    lg: 'px-5 py-2.5 text-sm font-semibold gap-2.5 h-10',
  };

  return (
    <button
      className={cn(
        baseStyles,
        variants[variant],
        sizes[size],
        className
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && <Spinner className="w-3.5 h-3.5 mr-1.5 text-current" />}
      {children}
    </button>
  );
};

export default Button;
