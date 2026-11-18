import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { LogOut, Database, UserCheck, Sparkles } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { checkForUpdates } from '../api/settings';
import { UpdateModal } from '../components/UpdateModal';

export const Topbar: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [showUpdateModal, setShowUpdateModal] = useState(false);

  const { data: updateData } = useQuery({
    queryKey: ['softwareUpdateCheck'],
    queryFn: () => checkForUpdates(false),
    staleTime: 1000 * 60 * 15,
  });

  const getPageInfo = () => {
    const path = location.pathname;
    if (path.startsWith('/history')) {
      return {
        title: 'Search History',
        desc: 'Consultation records & saved student queries',
      };
    }
    if (path.startsWith('/settings')) {
      return {
        title: 'System Settings & Releases',
        desc: 'App version, database overview, and desktop updates',
      };
    }
    return {
      title: 'Cutoff Search',
      desc: 'Candidate preference evaluation across CAP Rounds 1–4',
    };
  };

  const info = getPageInfo();

  return (
    <>
      <header className="bg-white border-b border-gray-200 h-16 flex items-center justify-between px-6 z-10 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div>
            <h2 className="text-base font-bold text-gray-900 leading-tight">
              {info.title}
            </h2>
            <p className="text-xs text-gray-500 hidden sm:block">
              {info.desc}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Update Available Quick Button */}
          {updateData?.update_available && (
            <button
              onClick={() => setShowUpdateModal(true)}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-300 rounded-full transition-colors shadow-xs"
              title="Click to view update details and download"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-600 animate-pulse" />
              <span>Update {updateData.latest_version} Available</span>
            </button>
          )}

          {/* Database Status */}
          <div className="hidden md:flex items-center text-xs font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
            <Database className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />
            <span>Cutoffs DB Online</span>
          </div>

          <div className="h-5 w-px bg-gray-200 hidden md:block" />

          {/* User & Logout */}
          <div className="flex items-center gap-3">
            <div className="flex items-center text-xs font-semibold text-gray-700">
              <UserCheck className="w-4 h-4 mr-1 text-primary-600" />
              <span>{user?.username || 'Admin'}</span>
            </div>

            <button
              onClick={logout}
              className="text-gray-400 hover:text-gray-700 hover:bg-gray-100 p-1.5 rounded-lg transition-colors"
              title="Logout from portal"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <UpdateModal
        isOpen={showUpdateModal}
        onClose={() => setShowUpdateModal(false)}
        updateData={updateData || null}
      />
    </>
  );
};

export default Topbar;
