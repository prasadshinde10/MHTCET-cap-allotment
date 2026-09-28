import React from 'react';
import { cn } from '../../utils/utils';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  padding?: boolean;
}

export const Card: React.FC<CardProps> = ({ children, className, title, subtitle, padding = true }) => {
  return (
    <div className={cn("bg-white overflow-hidden rounded-xl border border-slate-200/90 shadow-sm", className)}>
      {title && (
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 tracking-tight">{title}</h3>
            {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
          </div>
        </div>
      )}
      <div className={cn(padding && "p-5")}>
        {children}
      </div>
    </div>
  );
};

export const CardHeader: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => (
  <div className={cn("px-5 py-3.5 border-b border-slate-100", className)}>{children}</div>
);

export const CardTitle: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => (
  <h3 className={cn("text-sm font-semibold text-slate-900 tracking-tight", className)}>{children}</h3>
);

export const CardContent: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => (
  <div className={cn("p-5", className)}>{children}</div>
);

export default Card;
