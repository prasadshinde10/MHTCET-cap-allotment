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
        title: 'Candidate Consultation History',
        desc: 'Audit records & saved student counselling evaluations',
      };
    }
    if (path.startsWith('/imports')) {
      return {
        title: 'Admissions Data Ingestion & Parser',
        desc: 'Upload official CAP & JoSAA cutoff documents to populate admissions database',
      };
    }
    if (path.startsWith('/josaa')) {
      return {
        title: 'JoSAA Admissions Cutoff Explorer',
        desc: 'Joint Seat Allocation opening & closing ranks for IITs, NITs, IIITs & GFTIs',
      };
    }
    if (search.includes('panel=all_india')) {
      return {
        title: 'MHT-CET (All India Quota Cutoffs)',
        desc: 'JEE Main merit rank & percentile evaluation across participating institutes',
      };
    }
    return {
      title: 'MHT-CET (State Level Cutoffs)',
      desc: 'Maharashtra State Candidate quotas evaluation across CAP Rounds 1–4',
    };
  };

  const info = getPageInfo();

  return (
    <header className="bg-white border-b border-[#D9E2EC] h-14 flex items-center justify-between px-6 z-10 flex-shrink-0 select-none">
      <div className="flex items-center gap-3">
        <div>
          <h2 className="text-xs font-bold text-[#172B4D] tracking-tight leading-tight">
            {info.title}
          </h2>
          <p className="text-[11px] text-[#5B6B7F] hidden sm:block">
            {info.desc}
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-3.5">
        {/* Institutional Database Status Indicator */}
        <div className="hidden md:flex items-center text-[11px] font-medium text-[#16845B] bg-[#EAF7EE] px-2.5 py-1 rounded-full border border-[#B7E4C7]">
          <span className="relative flex h-2 w-2 mr-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#16845B] opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#16845B]"></span>
          </span>
          <Database className="w-3 h-3 mr-1 text-[#16845B]" />
          <span>Cutoffs DB Online</span>
        </div>

        <div className="h-4 w-px bg-[#D9E2EC] hidden md:block" />

        {/* User indicator */}
        <div className="flex items-center gap-2">
          <div className="flex items-center text-xs font-medium text-[#123B66] bg-[#EAF3FF] border border-[#ADCFFF] rounded-lg px-2.5 py-1">
            <UserCheck className="w-3.5 h-3.5 mr-1.5 text-[#1769D2]" />
            <span className="font-semibold">{user?.username || 'Administrator'}</span>
          </div>

          <button
            onClick={logout}
            className="text-[#5B6B7F] hover:text-[#C53030] hover:bg-[#FDF2F2] p-1.5 rounded-lg transition-colors border border-transparent hover:border-[#F8B4B4]"
            title="Sign Out"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
};

export default Topbar;
