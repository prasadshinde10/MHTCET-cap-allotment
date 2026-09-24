import React from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { LogOut } from 'lucide-react';

export const Topbar: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  // Simple title generation based on path
  const getPageTitle = () => {
    const path = location.pathname;
    if (path === '/dashboard') return 'Dashboard';
    if (path.startsWith('/colleges')) return 'Colleges';
    if (path.startsWith('/courses')) return 'Courses';
    if (path.startsWith('/cutoffs')) return 'Cutoffs';
    if (path === '/imports/new') return 'Import PDF';
    if (path === '/imports') return 'Import History';
    if (path.startsWith('/parser-errors')) return 'Parser Errors';
    if (path.startsWith('/analysis/round-comparison')) return 'Round Comparison';
    if (path.startsWith('/analysis/data-quality')) return 'Data Quality';
    if (path.startsWith('/settings')) return 'Settings';
    if (path.startsWith('/audit-logs')) return 'Audit Logs';
    return 'Admin Portal';
  };

  return (
    <div className="bg-white border-b border-gray-200 h-16 flex items-center justify-between px-6 z-10">
      <div className="flex items-center">
        <h2 className="text-xl font-semibold text-gray-800">{getPageTitle()}</h2>
      </div>
      <div className="flex items-center space-x-4">
        <div className="flex items-center text-sm font-medium text-gray-700">
          <span className="w-2 h-2 rounded-full bg-green-500 mr-2"></span>
          System Online
        </div>
        <div className="h-6 w-px bg-gray-300"></div>
        <div className="flex items-center">
          <span className="text-sm font-medium text-gray-700 mr-3">{user?.username || 'Admin'}</span>
          <button 
            onClick={logout}
            className="text-gray-500 hover:text-gray-700 p-1"
            title="Logout"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};
