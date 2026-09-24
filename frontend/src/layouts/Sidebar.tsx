import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, Building2, BookOpen, TableProperties, 
  Upload, History, AlertTriangle, GitCompare, CheckCircle, 
  Settings, FileText, LogOut
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { cn } from '../utils/utils';

export const Sidebar: React.FC = () => {
  const { logout } = useAuth();

  const navGroups = [
    {
      items: [
        { name: 'Dashboard', to: '/dashboard', icon: LayoutDashboard }
      ]
    },
    {
      header: 'Analysis & Insights',
      items: [
        { name: 'Cutoff Analysis', to: '/cutoffs', icon: TableProperties },
        { name: 'Round Comparison', to: '/analysis/round-comparison', icon: GitCompare },
        { name: 'Data Quality Audit', to: '/analysis/data-quality', icon: CheckCircle },
      ]
    },
    {
      header: 'CAP PDF Pipeline',
      items: [
        { name: 'Import CAP PDF', to: '/imports/new', icon: Upload },
        { name: 'Import History', to: '/imports', icon: History },
        { name: 'Parser Extraction Logs', to: '/parser-errors', icon: AlertTriangle },
      ]
    },
    {
      header: 'Extracted Master Data',
      items: [
        { name: 'Colleges Directory', to: '/colleges', icon: Building2 },
        { name: 'Courses Directory', to: '/courses', icon: BookOpen },
      ]
    },
    {
      header: 'Administration',
      items: [
        { name: 'Audit Log', to: '/audit-logs', icon: FileText },
        { name: 'System Settings', to: '/settings', icon: Settings },
      ]
    }
  ];

  return (
    <div className="flex flex-col w-64 bg-sidebar-800 border-r border-sidebar-900 min-h-screen text-gray-300">
      <div className="flex items-center justify-center h-16 bg-sidebar-900 border-b border-sidebar-800">
        <h1 className="text-white font-bold text-lg tracking-wide">CAP Cutoff Admin</h1>
      </div>
      <div className="flex-1 overflow-y-auto py-4">
        <nav className="px-2 space-y-4">
          {navGroups.map((group, idx) => (
            <div key={idx}>
              {group.header && (
                <h3 className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 mt-4">
                  {group.header}
                </h3>
              )}
              <div className="space-y-1">
                {group.items.map((item) => (
                  <NavLink
                    key={item.name}
                    to={item.to}
                    className={({ isActive }) => cn(
                      'group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                      isActive 
                        ? 'bg-primary-600 text-white' 
                        : 'text-gray-300 hover:bg-sidebar-900 hover:text-white'
                    )}
                  >
                    <item.icon className={cn(
                      'mr-3 flex-shrink-0 h-5 w-5'
                    )} aria-hidden="true" />
                    {item.name}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>
      </div>
      <div className="flex-shrink-0 flex border-t border-sidebar-900 p-4">
        <button
          onClick={logout}
          className="flex items-center w-full px-3 py-2 text-sm font-medium text-gray-300 rounded-md hover:bg-sidebar-900 hover:text-white transition-colors"
        >
          <LogOut className="mr-3 h-5 w-5" />
          Logout
        </button>
      </div>
    </div>
  );
};
