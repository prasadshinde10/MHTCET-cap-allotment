import React from 'react';
import { cn } from '../../utils/utils';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: React.ReactNode;
  padding?: boolean;
}

export const Card: React.FC<CardProps> = ({ children, className, title, padding = true }) => {
  return (
    <div className={cn("bg-white overflow-hidden shadow rounded-lg border border-gray-200", className)}>
      {title && (
        <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
          <h3 className="text-lg leading-6 font-medium text-gray-900">{title}</h3>
        </div>
      )}
      <div className={cn(padding && "px-4 py-5 sm:p-6")}>
        {children}
      </div>
    </div>
  );
};

export const CardHeader: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => (
  <div className={cn("px-4 py-5 sm:px-6 border-b border-gray-200", className)}>{children}</div>
);

export const CardTitle: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => (
  <h3 className={cn("text-lg leading-6 font-medium text-gray-900", className)}>{children}</h3>
);

export const CardContent: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => (
  <div className={cn("px-4 py-5 sm:p-6", className)}>{children}</div>
);

export default Card;
