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
      name: 'MHT-CET (State Quota)',
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
      name: 'JoSAA (IIT / NIT / IIIT)',
      to: '/josaa',
      icon: Award,
      badge: 'National',
      isActive: location.pathname.startsWith('/josaa'),
    },
    {
      name: 'Upload & Parse PDF',
      to: '/imports/new',
      icon: UploadCloud,
      badge: 'Ingest',
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
    <aside className="flex flex-col w-64 bg-[#0B2545] border-r border-[#1B4D82]/50 min-h-screen text-[#D9E2EC] flex-shrink-0 select-none">
      {/* Institutional Brand Header */}
      <div className="flex items-center px-4 h-16 bg-[#081D36] border-b border-[#1B4D82]/40 gap-3">
        <div className="w-9 h-9 rounded-lg bg-[#123B66] border border-[#1769D2]/40 flex items-center justify-center text-[#EAF3FF] shadow-xs flex-shrink-0">
          <GraduationCap className="w-5 h-5 text-[#80B3FF]" />
        </div>
        <div className="truncate">
          <div className="flex items-center gap-1.5">
            <h1 className="text-white font-semibold text-xs tracking-tight">Counselling Portal</h1>
            <span className="text-[9px] font-semibold uppercase px-1.5 py-0.2 bg-[#123B66] text-[#ADCFFF] rounded border border-[#1769D2]/30">
              Admin
            </span>
          </div>
          <p className="text-[10px] text-[#8292A2] font-medium truncate mt-0.5">
            Central Admissions System
          </p>
        </div>
      </div>

      {/* Navigation Modules */}
      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-4">
        <div>
          <div className="px-2 mb-2 text-[10px] font-bold text-[#8292A2] uppercase tracking-wider">
            Admissions Modules
          </div>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const active = item.isActive;
              return (
                <NavLink
                  key={item.name}
                  to={item.to}
                  className={cn(
                    'group flex items-center justify-between px-3 py-2 text-xs font-medium rounded-lg transition-all',
                    active
                      ? 'bg-[#123B66] text-white shadow-xs font-semibold border-l-2 border-[#1769D2]'
                      : 'text-[#D9E2EC] hover:bg-[#123B66]/50 hover:text-white'
                  )}
                >
                  <div className="flex items-center min-w-0">
                    <item.icon
                      className={cn(
                        'mr-2.5 flex-shrink-0 h-4 w-4 transition-colors',
                        active ? 'text-[#80B3FF]' : 'text-[#8292A2] group-hover:text-[#D9E2EC]'
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
                          ? 'bg-[#1769D2] text-white'
                          : 'bg-[#081D36] text-[#8292A2] group-hover:text-[#D9E2EC]'
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
      <div className="flex-shrink-0 border-t border-[#1B4D82]/40 p-3 bg-[#081D36]/70">
        <div className="flex items-center justify-between mb-2.5 px-1">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 rounded-full bg-[#123B66] border border-[#1769D2]/30 flex items-center justify-center text-[#80B3FF] flex-shrink-0">
              <ShieldCheck className="w-3.5 h-3.5" />
            </div>
            <div className="truncate text-left">
              <div className="text-xs font-semibold text-white truncate">
                {user?.username || 'Administrator'}
              </div>
              <div className="text-[10px] text-[#8292A2] truncate">
                {user?.email || 'admin@counselling.gov.in'}
              </div>
            </div>
          </div>
        </div>

        <button
          onClick={logout}
          className="flex items-center justify-center w-full px-2.5 py-1.5 text-xs font-medium text-[#D9E2EC] hover:text-white bg-[#123B66]/60 hover:bg-[#123B66] rounded-lg transition-colors border border-[#1B4D82]/40"
        >
          <LogOut className="mr-1.5 h-3.5 w-3.5 text-[#8292A2]" />
          Sign Out
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
