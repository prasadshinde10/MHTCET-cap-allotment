import React from 'react';
import { cn } from '../../utils/utils';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'success' | 'warning' | 'error' | 'info' | 'default' | 'navy';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'default', className }) => {
  const variants = {
    info: 'bg-[#EAF3FF] text-[#123B66] border-[#ADCFFF]',
    success: 'bg-[#EAF7EE] text-[#16845B] border-[#B7E4C7]',
    warning: 'bg-[#FEF7E6] text-[#B7791F] border-[#F7D070]',
    error: 'bg-[#FDF2F2] text-[#C53030] border-[#F8B4B4]',
    default: 'bg-[#F0F4F8] text-[#172B4D] border-[#D9E2EC]',
    navy: 'bg-[#0B2545] text-white border-[#123B66]',
  };

  return (
    <span className={cn(
      "inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold border tracking-wide select-none",
      variants[variant],
      className
    )}>
      {children}
    </span>
  );
};

export default Badge;
