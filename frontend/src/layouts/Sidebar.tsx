import React from 'react';
import { NavLink } from 'react-router-dom';
import { Search, History, LogOut, GraduationCap, ShieldCheck } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { cn } from '../utils/utils';

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuth();

  const navItems = [
    {
      name: 'Cutoff Search',
      to: '/search',
      icon: Search,
      badge: 'Primary',
    },
    {
      name: 'Search History',
      to: '/history',
      icon: History,
    },
  ];

  return (
    <aside className="flex flex-col w-64 bg-slate-900 border-r border-slate-800 min-h-screen text-slate-300">
      {/* Brand Header */}
      <div className="flex items-center px-5 h-16 bg-slate-950 border-b border-slate-800 gap-3">
        <div className="w-9 h-9 rounded-lg bg-primary-600 flex items-center justify-center text-white shadow-sm flex-shrink-0">
          <GraduationCap className="w-5 h-5" />
        </div>
        <div className="truncate">
          <h1 className="text-white font-bold text-sm tracking-tight truncate">
            CAP Admissions
          </h1>
          <p className="text-[11px] text-slate-400 font-medium truncate">
            Cutoff Counselling Portal
          </p>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto py-5 px-3">
        <div className="px-2 mb-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
          Admissions Navigation
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'group flex items-center justify-between px-3 py-2.5 text-sm font-medium rounded-lg transition-colors',
                  isActive
                    ? 'bg-primary-600 text-white shadow-sm'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                )
              }
            >
              <div className="flex items-center">
                <item.icon
                  className="mr-3 flex-shrink-0 h-4 w-4 text-slate-400 group-hover:text-white"
                  aria-hidden="true"
                />
                <span>{item.name}</span>
              </div>
              {item.badge && (
                <span className="text-[10px] uppercase font-semibold tracking-wider px-1.5 py-0.5 rounded bg-slate-800 text-primary-300 group-hover:bg-primary-700 group-hover:text-white">
                  {item.badge}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* User Info & Logout Footer */}
      <div className="flex-shrink-0 border-t border-slate-800 p-4 bg-slate-950/60">
        <div className="flex items-center justify-between mb-3 px-1">
          <div className="flex items-center gap-2 truncate">
            <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-primary-400 flex-shrink-0">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div className="truncate text-left">
              <div className="text-xs font-semibold text-white truncate">
                {user?.username || 'Admin Counsellor'}
              </div>
              <div className="text-[10px] text-slate-400 truncate">
                {user?.email || 'admin@capportal.com'}
              </div>
            </div>
          </div>
        </div>

        <button
          onClick={logout}
          className="flex items-center justify-center w-full px-3 py-2 text-xs font-medium text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-800 rounded-lg transition-colors border border-slate-700/60"
        >
          <LogOut className="mr-2 h-3.5 w-3.5 text-slate-400" />
          Logout
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
