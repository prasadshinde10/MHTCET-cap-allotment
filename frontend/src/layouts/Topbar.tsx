import React from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { LogOut, Database, UserCheck } from 'lucide-react';

export const Topbar: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const getPageInfo = () => {
    const path = location.pathname;
    const search = location.search;

    if (path.startsWith('/history')) {
      return {
        title: 'Search History',
        desc: 'Consultation records & saved student queries',
      };
    }
    if (path.startsWith('/imports')) {
      return {
        title: 'PDF Parser & Ingestion',
        desc: 'Upload official CAP cutoff PDFs to populate real-time database',
      };
    }
    if (path.startsWith('/josaa')) {
      return {
        title: 'JoSAA Admissions Explorer',
        desc: 'Cutoff analysis for IITs, NITs, IIITs & GFTIs (Rounds 1–5)',
      };
    }
    if (search.includes('panel=all_india')) {
      return {
        title: 'MHT-CET (All India Cutoff)',
        desc: 'JEE Main merit rank & percentile evaluation across Maharashtra institutes',
      };
    }
    return {
      title: 'MHT-CET (State Cutoff)',
      desc: 'Maharashtra State Candidate quotas evaluation across CAP Rounds 1–4',
    };
  };

  const info = getPageInfo();

  return (
    <header className="bg-white border-b border-slate-200/90 h-14 flex items-center justify-between px-6 z-10 flex-shrink-0 select-none">
      <div className="flex items-center gap-3">
        <div>
          <h2 className="text-xs font-bold text-slate-900 tracking-tight leading-tight">
            {info.title}
          </h2>
          <p className="text-[11px] text-slate-500 hidden sm:block">
            {info.desc}
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-3.5">
        {/* Database Status Indicator */}
        <div className="hidden md:flex items-center text-[11px] font-medium text-slate-600 bg-slate-50 px-2.5 py-1 rounded-full border border-slate-200/80">
          <span className="relative flex h-2 w-2 mr-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <Database className="w-3 h-3 mr-1 text-slate-400" />
          <span>Cutoffs DB Online</span>
        </div>

        <div className="h-4 w-px bg-slate-200 hidden md:block" />

        {/* User badge */}
        <div className="flex items-center gap-2">
          <div className="flex items-center text-xs font-medium text-slate-700 bg-slate-50 border border-slate-200/60 rounded-lg px-2 py-1">
            <UserCheck className="w-3.5 h-3.5 mr-1 text-blue-600" />
            <span className="font-semibold">{user?.username || 'Admin'}</span>
          </div>

          <button
            onClick={logout}
            className="text-slate-400 hover:text-rose-600 hover:bg-rose-50 p-1.5 rounded-lg transition-colors border border-transparent hover:border-rose-100"
            title="Logout"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
};

export default Topbar;
