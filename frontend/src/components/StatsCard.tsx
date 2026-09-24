import React from 'react';
import { Card } from './ui/Card';
import { LucideIcon, Activity } from 'lucide-react';

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
}

export const StatsCard: React.FC<StatsCardProps> = ({
  title,
  label,
  value,
  icon: Icon = Activity,
  color,
  iconColor,
  iconBg,
  trend,
  subtitle
}) => {
  const displayLabel = title || label || '';
  const resolvedIconColor = iconColor || (color ? `text-${color}-600` : 'text-primary-600');
  const resolvedIconBg = iconBg || (color ? `bg-${color}-100` : 'bg-primary-100');

  return (
    <Card className="flex items-center p-5">
      <div className={`p-3 rounded-md ${resolvedIconBg} ${resolvedIconColor} mr-5`}>
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <p className="text-sm font-medium text-gray-500 truncate">{displayLabel}</p>
        <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
        {(trend || subtitle) && (
          <p className="mt-1 text-sm text-gray-500">
            {trend && <span className="text-green-600 font-medium mr-2">{trend}</span>}
            {subtitle}
          </p>
        )}
      </div>
    </Card>
  );
};

export default StatsCard;
