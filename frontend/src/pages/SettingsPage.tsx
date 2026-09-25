import { useQuery } from '@tanstack/react-query';
import { getSystemSettings } from '../api/settings';
import Card from '../components/ui/Card';
import Spinner from '../components/ui/Spinner';

export function SettingsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: getSystemSettings,
  });

  if (isLoading) return <div className="p-8 flex justify-center"><Spinner /></div>;
  if (!data) return <div className="p-8 text-center text-red-500">Failed to load system settings</div>;

  const dbStats = data.db_stats || {};
  const storageInfo = data.storage_info || {};

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">System Information & Settings</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="Application Information">
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
              <dd className="text-gray-900 capitalize">Development (SQLite)</dd>
            </div>
            <div className="py-2.5 flex justify-between">
              <dt className="font-medium text-gray-500">Last Import Timestamp</dt>
              <dd className="text-gray-900">
                {storageInfo.last_import_date ? new Date(storageInfo.last_import_date).toLocaleString() : 'No imports yet'}
              </dd>
            </div>
          </dl>
        </Card>

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
  );
}
