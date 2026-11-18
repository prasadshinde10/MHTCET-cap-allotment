import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { checkForUpdates } from '../api/settings';
import { Sparkles, Download, X, ArrowRight } from 'lucide-react';
import { UpdateModal } from './UpdateModal';

export const UpdateNotificationBanner: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  const { data: updateData } = useQuery({
    queryKey: ['softwareUpdateCheck'],
    queryFn: () => checkForUpdates(false),
    staleTime: 1000 * 60 * 15, // 15 minutes
    retry: 1,
  });

  if (!updateData || !updateData.update_available || isDismissed) {
    return (
      <UpdateModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        updateData={updateData || null}
      />
    );
  }

  const sessionDismissKey = `dismissed_update_${updateData.latest_version}`;
  if (sessionStorage.getItem(sessionDismissKey)) {
    return (
      <UpdateModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        updateData={updateData}
      />
    );
  }

  const handleDismiss = () => {
    setIsDismissed(true);
    sessionStorage.setItem(sessionDismissKey, 'true');
  };

  return (
    <>
      <div className="bg-gradient-to-r from-indigo-900 via-primary-900 to-slate-900 text-white px-4 py-2.5 text-xs border-b border-indigo-700/40 shadow-sm flex items-center justify-between z-20 flex-shrink-0 animate-in slide-in-from-top duration-300">
        <div className="flex items-center gap-2.5 flex-1 min-w-0 pr-4">
          <span className="flex h-2 w-2 relative flex-shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
          </span>
          <div className="flex items-center gap-2 truncate">
            <span className="font-bold text-amber-300 uppercase tracking-wider text-[10px] bg-amber-500/20 px-1.5 py-0.5 rounded border border-amber-400/30">
              New Update
            </span>
            <span className="font-semibold text-white truncate">
              {updateData.release_title || `Version ${updateData.latest_version}`} is now available!
            </span>
            <span className="text-slate-300 hidden sm:inline">
              (You are currently running {updateData.current_version})
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1 bg-primary-600 hover:bg-primary-500 text-white font-medium rounded-md shadow transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Update Now</span>
            <ArrowRight className="w-3 h-3 ml-0.5" />
          </button>
          <button
            onClick={handleDismiss}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-white/10 transition-colors"
            title="Dismiss notice"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <UpdateModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        updateData={updateData}
      />
    </>
  );
};

export default UpdateNotificationBanner;
