import React from 'react';
import { LucideIcon, Activity } from 'lucide-react';
import { cn } from '../utils/utils';

interface StatsCardProps {
  title?: string;
  label?: string;
  value: string | number;
  icon?: LucideIcon;
  color?: string;
  iconColor?: string;
  iconBg?: string;
  trend?: string;
  subtitle?: string;
  className?: string;
}

export const StatsCard: React.FC<StatsCardProps> = ({
  title,
  label,
  value,
  icon: Icon = Activity,
  iconColor = 'text-blue-600',
  iconBg = 'bg-blue-50 border-blue-200/60',
  trend,
  subtitle,
  className
}) => {
  const displayLabel = title || label || '';

  return (
    <div className={cn("bg-white rounded-xl border border-slate-200/90 p-4 shadow-sm flex items-center justify-between gap-3", className)}>
      <div className="min-w-0">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 truncate">{displayLabel}</p>
        <p className="mt-1 text-xl font-bold text-slate-900 tracking-tight">{value}</p>
        {(trend || subtitle) && (
          <p className="mt-0.5 text-[11px] text-slate-500 truncate">
            {trend && <span className="text-emerald-600 font-semibold mr-1.5">{trend}</span>}
            {subtitle}
          </p>
        )}
      </div>
      <div className={cn("w-10 h-10 rounded-lg border flex items-center justify-center flex-shrink-0", iconBg, iconColor)}>
        <Icon className="w-5 h-5" />
      </div>
    </div>
  );
};

export default StatsCard;
