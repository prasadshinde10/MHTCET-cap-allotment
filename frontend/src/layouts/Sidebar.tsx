import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Search, History, LogOut, GraduationCap, ShieldCheck, UploadCloud, Award, Sparkles } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { cn } from '../utils/utils';

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const isStateActive = location.pathname === '/search' && (!location.search || location.search.includes('panel=state'));
  const isAllIndiaActive = location.pathname === '/search' && location.search.includes('panel=all_india');

  const navItems = [
    {
      name: 'MHT-CET (State)',
      to: '/search?panel=state',
      icon: Search,
      badge: 'State',
      isActive: isStateActive,
    },
    {
      name: 'MHT-CET (All India)',
      to: '/search?panel=all_india',
      icon: Sparkles,
      badge: 'JEE/AI',
      isActive: isAllIndiaActive,
    },
    {
      name: 'JoSAA (IIT / NIT)',
      to: '/josaa',
      icon: Award,
      badge: 'National',
      isActive: location.pathname.startsWith('/josaa'),
    },
    {
      name: 'Upload & Parse PDF',
      to: '/imports/new',
      icon: UploadCloud,
      badge: 'Sync',
      isActive: location.pathname.startsWith('/imports'),
    },
    {
      name: 'Search History',
      to: '/history',
      icon: History,
      isActive: location.pathname.startsWith('/history'),
    },
  ];

  return (
    <aside className="flex flex-col w-60 bg-slate-900 border-r border-slate-800/80 min-h-screen text-slate-300 flex-shrink-0 select-none">
      {/* Brand Header */}
      <div className="flex items-center px-4 h-14 bg-slate-950/80 border-b border-slate-800/80 gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-sm flex-shrink-0">
          <GraduationCap className="w-4 h-4" />
        </div>
        <div className="truncate">
          <div className="flex items-center gap-1.5">
            <h1 className="text-white font-semibold text-xs tracking-tight">CAP Portal</h1>
            <span className="text-[9px] font-semibold uppercase px-1 py-0.2 bg-blue-500/20 text-blue-300 rounded border border-blue-400/20">
              Admin
            </span>
          </div>
          <p className="text-[10px] text-slate-400 font-medium truncate mt-0.5">
            Engineering Admissions
          </p>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto py-4 px-2.5 space-y-4">
        <div>
          <div className="px-2 mb-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-widest">
            Admissions Modules
          </div>
          <nav className="space-y-0.5">
            {navItems.map((item) => {
              const active = item.isActive;
              return (
                <NavLink
                  key={item.name}
                  to={item.to}
                  className={cn(
                    'group flex items-center justify-between px-2.5 py-2 text-xs font-medium rounded-lg transition-all',
                    active
                      ? 'bg-blue-600 text-white shadow-sm font-semibold'
                      : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                  )}
                >
                  <div className="flex items-center min-w-0">
                    <item.icon
                      className={cn(
                        'mr-2.5 flex-shrink-0 h-4 w-4 transition-colors',
                        active ? 'text-white' : 'text-slate-400 group-hover:text-slate-200'
                      )}
                      aria-hidden="true"
                    />
                    <span className="truncate">{item.name}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={cn(
                        'text-[10px] uppercase font-semibold tracking-wider px-1.5 py-0.5 rounded transition-colors ml-1.5 flex-shrink-0',
                        active
                          ? 'bg-blue-700/80 text-white'
                          : 'bg-slate-800 text-slate-400 group-hover:text-slate-200'
                      )}
                    >
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>
      </div>

      {/* User Info & Logout Footer */}
      <div className="flex-shrink-0 border-t border-slate-800/80 p-3 bg-slate-950/60">
        <div className="flex items-center justify-between mb-2.5 px-1">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700/80 flex items-center justify-center text-blue-400 flex-shrink-0">
              <ShieldCheck className="w-3.5 h-3.5" />
            </div>
            <div className="truncate text-left">
              <div className="text-xs font-semibold text-slate-200 truncate">
                {user?.username || 'Administrator'}
              </div>
              <div className="text-[10px] text-slate-500 truncate">
                {user?.email || 'admin@capportal.com'}
              </div>
            </div>
          </div>
        </div>

        <button
          onClick={logout}
          className="flex items-center justify-center w-full px-2.5 py-1.5 text-xs font-medium text-slate-400 hover:text-white bg-slate-800/60 hover:bg-slate-800 rounded-lg transition-colors border border-slate-700/50"
        >
          <LogOut className="mr-1.5 h-3.5 w-3.5 text-slate-400" />
          Logout
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
