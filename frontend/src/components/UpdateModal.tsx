import React, { useState, useEffect, useRef } from 'react';
import {
  Download,
  ExternalLink,
  Sparkles,
  X,
  Calendar,
  FileArchive,
  CheckCircle2,
  RefreshCw,
  Zap,
  AlertTriangle,
  Loader2,
  RotateCcw,
} from 'lucide-react';
import {
  UpdateCheckResult,
  UpdateProgressResult,
  getUpdateProgress,
  startInPlaceUpdate,
  restartAndApplyUpdate,
} from '../api/settings';
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
  const [progress, setProgress] = useState<UpdateProgressResult | null>(null);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [isRestarting, setIsRestarting] = useState<boolean>(false);
  const pollingTimerRef = useRef<number | null>(null);

  const stopPolling = () => {
    if (pollingTimerRef.current !== null) {
      window.clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
  };

  // Poll update progress
  const pollStatus = async () => {
    try {
      const p = await getUpdateProgress();
      setProgress(p);

      if (p.status === 'downloading' || p.status === 'extracting') {
        setIsUpdating(true);
      } else if (p.status === 'ready') {
        stopPolling();
        setIsUpdating(false);
        setIsRestarting(true);
        // Automatically trigger restart & apply
        try {
          await restartAndApplyUpdate();
        } catch (e) {
          console.error('Restart trigger error:', e);
        }
      } else if (p.status === 'failed') {
        stopPolling();
        setIsUpdating(false);
      }
    } catch (e) {
      console.warn('Error fetching update progress:', e);
    }
  };

  // Check progress when modal opens or on mount
  useEffect(() => {
    if (isOpen) {
      pollStatus();
    } else {
      stopPolling();
    }
    return () => stopPolling();
  }, [isOpen]);

  const handleStartInPlaceUpdate = async () => {
    setIsUpdating(true);
    setIsRestarting(false);
    try {
      const res = await startInPlaceUpdate();
      if (res.progress) {
        setProgress(res.progress);
      }
      stopPolling();
      pollingTimerRef.current = window.setInterval(pollStatus, 500);
    } catch (e: any) {
      setIsUpdating(false);
      setProgress((prev) => ({
        status: 'failed',
        progress_percent: 0,
        downloaded_bytes: 0,
        total_bytes: 0,
        downloaded_mb: 0,
        total_mb: 0,
        message: 'Could not connect to update service',
        target_version: updateData?.latest_version || '',
        error: e?.response?.data?.detail || e?.message || 'Connection failure',
      }));
    }
  };

  const handleDownload = () => {
    if (updateData?.download_url) {
      window.open(updateData.download_url, '_blank', 'noopener,noreferrer');
    }
  };

  const handleOpenGitHub = () => {
    if (updateData?.release_url) {
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

  if (!isOpen || !updateData) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-xl w-full border border-slate-100 overflow-hidden transform transition-all animate-in fade-in zoom-in-95 duration-200"
        role="dialog"
        aria-modal="true"
      >
        {/* Modal Header */}
        <div className="bg-gradient-to-r from-primary-600 via-primary-700 to-indigo-800 p-6 text-white relative">
          {!isUpdating && !isRestarting && (
            <button
              onClick={onClose}
              className="absolute top-4 right-4 text-white/80 hover:text-white hover:bg-white/10 p-1.5 rounded-full transition-colors"
              title="Close dialog"
            >
              <X className="w-5 h-5" />
            </button>
          )}

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
          {/* In-Place Update Progress Card (Active Update State) */}
          {isUpdating || isRestarting ? (
            <div className="p-5 bg-gradient-to-br from-indigo-50/70 to-blue-50/70 border border-indigo-200 rounded-xl space-y-3.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 bg-indigo-600 text-white rounded-lg shadow-sm">
                    {isRestarting ? (
                      <RotateCcw className="w-5 h-5 animate-spin" />
                    ) : (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    )}
                  </div>
                  <div>
                    <div className="text-sm font-bold text-slate-800">
                      {isRestarting
                        ? 'Restarting Application...'
                        : progress?.status === 'extracting'
                        ? 'Extracting Package Files...'
                        : 'Downloading Silent Update...'}
                    </div>
                    <div className="text-xs text-slate-600">
                      {isRestarting
                        ? 'Applying new files and restarting. Browser will reconnect in seconds...'
                        : progress?.message || 'Preparing update files...'}
                    </div>
                  </div>
                </div>
                <div className="text-xs font-mono font-bold text-indigo-700 bg-indigo-100/80 px-2.5 py-1 rounded-md">
                  {isRestarting ? '100%' : `${progress?.progress_percent || 0}%`}
                </div>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-slate-200/80 rounded-full h-3 overflow-hidden p-0.5 border border-slate-300/50">
                <div
                  className="bg-gradient-to-r from-indigo-600 to-primary-500 h-full rounded-full transition-all duration-300 ease-out shadow-sm"
                  style={{
                    width: `${isRestarting ? 100 : Math.max(3, progress?.progress_percent || 0)}%`,
                  }}
                />
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono">
                <span>
                  {progress?.downloaded_mb
                    ? `${progress.downloaded_mb} MB / ${progress.total_mb} MB`
                    : 'Target package: ~124 MB'}
                </span>
                <span className="text-indigo-600 font-medium">
                  {isRestarting ? 'Finalizing in-place upgrade' : 'Zero-touch automated update'}
                </span>
              </div>
            </div>
          ) : progress?.status === 'failed' ? (
            /* Error Card */
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl space-y-2">
              <div className="flex items-center gap-2 text-rose-800 font-semibold text-xs">
                <AlertTriangle className="w-4 h-4 text-rose-500" />
                <span>Auto-Update Failed</span>
              </div>
              <p className="text-xs text-rose-700">
                {progress.error || 'The update package could not be downloaded or extracted.'}
              </p>
              <div className="flex items-center gap-2 pt-1">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleStartInPlaceUpdate}
                  className="flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Retry Auto-Update</span>
                </Button>
                {updateData.download_url && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleDownload}
                    className="flex items-center gap-1.5"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download Manually</span>
                  </Button>
                )}
              </div>
            </div>
          ) : (
            /* Idle Ready Card */
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-primary-100 text-primary-700 rounded-lg">
                  <FileArchive className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-800">
                    {updateData.asset_name || `CAP_Portal-${updateData.latest_version}.zip`}
                  </div>
                  <div className="text-xs text-slate-500">
                    {updateData.asset_size_mb
                      ? `${updateData.asset_size_mb} MB`
                      : 'Windows Desktop Build / Update Archive'}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="primary"
                  onClick={handleStartInPlaceUpdate}
                  className="flex items-center gap-1.5 shadow-sm bg-gradient-to-r from-primary-600 to-indigo-600 hover:from-primary-700 hover:to-indigo-700 text-white"
                >
                  <Zap className="w-4 h-4 text-amber-300" />
                  <span>Update & Restart</span>
                </Button>
              </div>
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
          ) : (
            <div />
          )}

          <div className="flex items-center gap-3">
            {!isUpdating && !isRestarting && (
              <>
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-200 rounded-lg transition-colors"
                >
                  Remind Me Later
                </button>
                {updateData.download_url && (
                  <button
                    onClick={handleDownload}
                    className="text-xs text-slate-500 hover:text-primary-600 underline font-medium"
                    title="Download ZIP package manually"
                  >
                    Download ZIP Manually
                  </button>
                )}
              </>
            )}
            {isRestarting && (
              <span className="text-xs text-indigo-600 font-medium animate-pulse">
                Please wait, restarting...
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UpdateModal;
