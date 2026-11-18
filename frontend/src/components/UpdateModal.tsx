import React from 'react';
import { Download, ExternalLink, Sparkles, X, Calendar, FileArchive, CheckCircle2 } from 'lucide-react';
import { UpdateCheckResult } from '../api/settings';
import Button from './ui/Button';

interface UpdateModalProps {
  isOpen: boolean;
  onClose: () => void;
  updateData: UpdateCheckResult | null;
}

export const UpdateModal: React.FC<UpdateModalProps> = ({
  isOpen,
  onClose,
  updateData,
}) => {
  if (!isOpen || !updateData) return null;

  const handleDownload = () => {
    if (updateData.download_url) {
      window.open(updateData.download_url, '_blank', 'noopener,noreferrer');
    }
  };

  const handleOpenGitHub = () => {
    if (updateData.release_url) {
      window.open(updateData.release_url, '_blank', 'noopener,noreferrer');
    }
  };

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return '';
    try {
      return new Date(isoString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div 
        className="bg-white rounded-2xl shadow-2xl max-w-xl w-full border border-slate-100 overflow-hidden transform transition-all animate-in fade-in zoom-in-95 duration-200"
        role="dialog"
        aria-modal="true"
      >
        {/* Modal Header */}
        <div className="bg-gradient-to-r from-primary-600 via-primary-700 to-indigo-800 p-6 text-white relative">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-white/80 hover:text-white hover:bg-white/10 p-1.5 rounded-full transition-colors"
            title="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-3 mb-2">
            <span className="p-2 bg-white/15 rounded-xl backdrop-blur-sm">
              <Sparkles className="w-6 h-6 text-amber-300" />
            </span>
            <div>
              <span className="inline-block text-[11px] font-bold tracking-wider uppercase text-amber-300 font-mono">
                Software Update Available
              </span>
              <h3 className="text-xl font-bold tracking-tight">
                {updateData.release_title || `Version ${updateData.latest_version}`}
              </h3>
            </div>
          </div>

          {/* Version comparison row */}
          <div className="flex items-center gap-3 mt-4 text-xs font-mono">
            <div className="bg-black/20 px-3 py-1.5 rounded-lg border border-white/10 flex items-center gap-2">
              <span className="text-white/70">Current:</span>
              <span className="font-semibold text-white">{updateData.current_version}</span>
            </div>
            <span className="text-white/60">→</span>
            <div className="bg-emerald-500/25 text-emerald-200 px-3 py-1.5 rounded-lg border border-emerald-400/30 flex items-center gap-2 font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-300" />
              <span>Latest: {updateData.latest_version}</span>
            </div>
            {updateData.published_at && (
              <div className="ml-auto flex items-center gap-1 text-white/70">
                <Calendar className="w-3.5 h-3.5" />
                <span>{formatDate(updateData.published_at)}</span>
              </div>
            )}
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
          {/* Asset Download Card */}
          {updateData.download_url && (
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-primary-100 text-primary-700 rounded-lg">
                  <FileArchive className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-800">
                    {updateData.asset_name || 'Software Release Package'}
                  </div>
                  <div className="text-xs text-slate-500">
                    {updateData.asset_size_mb ? `${updateData.asset_size_mb} MB` : 'Windows Desktop Build / Update Archive'}
                  </div>
                </div>
              </div>
              <Button
                variant="primary"
                onClick={handleDownload}
                className="flex items-center gap-1.5 shadow-sm"
              >
                <Download className="w-4 h-4" />
                <span>Download</span>
              </Button>
            </div>
          )}

          {/* Release Notes */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
              What's New in this Release
            </h4>
            {updateData.release_notes ? (
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs font-mono whitespace-pre-wrap text-slate-700 leading-relaxed max-h-56 overflow-y-auto">
                {updateData.release_notes}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">
                Performance enhancements, updated CAP cutoffs, and bug fixes included.
              </p>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="bg-slate-50 border-t border-slate-100 px-6 py-4 flex items-center justify-between">
          {updateData.release_url ? (
            <button
              onClick={handleOpenGitHub}
              className="text-xs font-medium text-slate-600 hover:text-primary-600 flex items-center gap-1.5 transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>View Release on GitHub</span>
            </button>
          ) : <div />}

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-200 rounded-lg transition-colors"
            >
              Remind Me Later
            </button>
            {updateData.download_url && (
              <Button
                variant="primary"
                onClick={handleDownload}
                className="flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                <span>Download ZIP ({updateData.asset_size_mb || 'Full'} MB)</span>
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UpdateModal;
