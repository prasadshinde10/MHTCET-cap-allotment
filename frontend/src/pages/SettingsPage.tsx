import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getSystemSettings, checkForUpdates, UpdateCheckResult } from '../api/settings';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Spinner from '../components/ui/Spinner';
import { Sparkles, RefreshCw, Download, CheckCircle2, AlertCircle, ExternalLink } from 'lucide-react';
import { UpdateModal } from '../components/UpdateModal';
import toast from 'react-hot-toast';

export function SettingsPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeUpdateData, setActiveUpdateData] = useState<UpdateCheckResult | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: getSystemSettings,
  });

  const { data: updateData, isLoading: isUpdateLoading, refetch: checkUpdateRefetch } = useQuery({
    queryKey: ['softwareUpdateCheck'],
    queryFn: () => checkForUpdates(false),
    staleTime: 1000 * 60 * 15,
  });

  const checkMutation = useMutation({
    mutationFn: () => checkForUpdates(true),
    onSuccess: (res) => {
      setActiveUpdateData(res);
      if (res.update_available) {
        toast.success(`New version ${res.latest_version} available!`);
      } else if (res.error) {
        toast.error(res.error);
      } else {
        toast.success('Your portal is already up to date!');
      }
    },
    onError: (err: any) => {
      toast.error(err.message || 'Failed to check GitHub releases');
    },
  });

  const effectiveUpdate = activeUpdateData || updateData;

  if (isLoading) return <div className="p-8 flex justify-center"><Spinner /></div>;
  if (!data) return <div className="p-8 text-center text-red-500">Failed to load system settings</div>;

  const dbStats = data.db_stats || {};
  const storageInfo = data.storage_info || {};

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Information & Settings</h1>
          <p className="text-xs text-gray-500 mt-0.5">Software version, GitHub releases, and database statistics</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Software Releases & Updates Card */}
        <div className="lg:col-span-1">
          <Card title="Software Version & Releases">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-gray-100">
                <span className="text-xs text-gray-500 font-medium">Installed Version</span>
                <span className="font-mono text-sm font-bold text-gray-900 bg-gray-100 px-2 py-0.5 rounded">
                  v{data.app_version || '1.0.0'}
                </span>
              </div>

              {/* Status Box */}
              {isUpdateLoading || checkMutation.isPending ? (
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center gap-3">
                  <Spinner className="w-4 h-4 text-primary-600" />
                  <span className="text-xs text-slate-600">Checking GitHub releases...</span>
                </div>
              ) : effectiveUpdate?.update_available ? (
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-2.5">
                  <div className="flex items-center gap-2 text-amber-800 font-bold text-xs">
                    <Sparkles className="w-4 h-4 text-amber-600" />
                    <span>New Version {effectiveUpdate.latest_version} Available!</span>
                  </div>
                  <p className="text-[11px] text-amber-700">
                    {effectiveUpdate.release_title || 'An updated release has been published with new features and datasets.'}
                  </p>
                  <div className="flex items-center gap-2 pt-1">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => setIsModalOpen(true)}
                      className="w-full flex items-center justify-center gap-1.5 shadow-xs"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>View Update & Download</span>
                    </Button>
                  </div>
                </div>
              ) : effectiveUpdate?.error ? (
                <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5">
                  <AlertCircle className="w-4 h-4 text-rose-500 flex-shrink-0 mt-0.5" />
                  <div className="text-xs text-rose-700">
                    <div className="font-semibold">Update check offline</div>
                    <div className="text-[11px] text-rose-600 mt-0.5">{effectiveUpdate.error}</div>
                  </div>
                </div>
              ) : (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                  <div>
                    <div className="text-xs font-bold text-emerald-800">You are up to date!</div>
                    <div className="text-[11px] text-emerald-600">Running the latest release.</div>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center gap-2 pt-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => checkMutation.mutate()}
                  isLoading={checkMutation.isPending}
                  className="w-full flex items-center justify-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Check for Updates</span>
                </Button>
              </div>

              {effectiveUpdate?.release_url && (
                <div className="text-center pt-1">
                  <a
                    href={effectiveUpdate.release_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[11px] text-slate-500 hover:text-primary-600 font-medium"
                  >
                    <span>View GitHub Releases Page</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Application Information Card */}
        <div className="lg:col-span-1">
          <Card title="Application Environment">
            <dl className="divide-y divide-gray-100 text-sm">
              <div className="py-2.5 flex justify-between">
                <dt className="font-medium text-gray-500">App Version</dt>
                <dd className="font-mono text-gray-900">{data.app_version || '1.0.0'}</dd>
              </div>
              <div className="py-2.5 flex justify-between">
                <dt className="font-medium text-gray-500">Parser Engine Version</dt>
                <dd className="font-mono text-gray-900">{data.parser_version || '1.0.0'}</dd>
              </div>
              <div className="py-2.5 flex justify-between">
                <dt className="font-medium text-gray-500">Environment</dt>
                <dd className="text-gray-900 capitalize">Desktop Standalone (SQLite)</dd>
              </div>
              <div className="py-2.5 flex justify-between">
                <dt className="font-medium text-gray-500">Last Import Timestamp</dt>
                <dd className="text-gray-900 text-xs">
                  {storageInfo.last_import_date ? new Date(storageInfo.last_import_date).toLocaleString() : 'No imports yet'}
                </dd>
              </div>
            </dl>
          </Card>
        </div>

        {/* Database Overview Card */}
        <div className="lg:col-span-1">
          <Card title="Database Overview">
            <dl className="divide-y divide-gray-100 text-sm">
              <div className="py-2.5 flex justify-between">
                <dt className="font-medium text-gray-500">Total Colleges</dt>
                <dd className="font-mono font-semibold text-gray-900">{dbStats.total_colleges || 0}</dd>
              </div>
              <div className="py-2.5 flex justify-between">
                <dt className="font-medium text-gray-500">Total Courses</dt>
                <dd className="font-mono font-semibold text-gray-900">{dbStats.total_courses || 0}</dd>
              </div>
              <div className="py-2.5 flex justify-between">
                <dt className="font-medium text-gray-500">Total Cutoff Records</dt>
                <dd className="font-mono font-semibold text-gray-900">{dbStats.total_cutoffs || 0}</dd>
              </div>
              <div className="py-2.5 flex justify-between">
                <dt className="font-medium text-gray-500">Processed Import Batches</dt>
                <dd className="font-mono font-semibold text-gray-900">{dbStats.total_imports || 0}</dd>
              </div>
            </dl>
          </Card>
        </div>
      </div>

      <UpdateModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        updateData={effectiveUpdate || null}
      />
    </div>
  );
}

export default SettingsPage;
