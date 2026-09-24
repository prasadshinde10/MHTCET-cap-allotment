import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAuditLogs, AuditLog } from '../api/auditLogs';
import Card from '../components/ui/Card';
import Select from '../components/ui/Select';
import Spinner from '../components/ui/Spinner';
import Pagination from '../components/ui/Pagination';

export function AuditLogsPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [action, setAction] = useState('');
  const [entityType, setEntityType] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['audit-logs', page, pageSize, action, entityType],
    queryFn: () => getAuditLogs({ page, page_size: pageSize, action: action || undefined, entity_type: entityType || undefined }),
  });

  const logItems = data?.items || [];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Audit Logs</h1>

      <Card className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Select 
            label="Action" 
            value={action} 
            onChange={(e) => setAction(e.target.value)}
            options={[
              { value: '', label: 'All Actions' },
              { value: 'CREATE', label: 'Create' },
              { value: 'UPDATE', label: 'Update' },
              { value: 'DELETE', label: 'Delete' },
              { value: 'LOGIN', label: 'Login' },
              { value: 'IMPORT', label: 'Import' },
            ]}
          />
          <Select 
            label="Entity Type" 
            value={entityType} 
            onChange={(e) => setEntityType(e.target.value)}
            options={[
              { value: '', label: 'All Entities' },
              { value: 'cutoff', label: 'Cutoff' },
              { value: 'college', label: 'College' },
              { value: 'course', label: 'Course' },
              { value: 'admin_user', label: 'Admin User' },
              { value: 'import_batch', label: 'Import Batch' },
            ]}
          />
        </div>
      </Card>

      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="p-8 flex justify-center"><Spinner /></div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timestamp</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Entity Type</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Entity ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">IP Address</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Details</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200 text-sm">
                  {logItems.length === 0 ? (
                    <tr><td colSpan={6} className="px-6 py-8 text-center text-sm text-gray-500">No audit logs found.</td></tr>
                  ) : (
                    logItems.map((log: AuditLog) => (
                      <tr key={log.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 whitespace-nowrap text-gray-500">{new Date(log.created_at).toLocaleString()}</td>
                        <td className="px-4 py-3 whitespace-nowrap font-medium text-gray-900">{log.action}</td>
                        <td className="px-4 py-3 whitespace-nowrap text-gray-600">{log.entity_type}</td>
                        <td className="px-4 py-3 whitespace-nowrap text-gray-500">{log.entity_id || '-'}</td>
                        <td className="px-4 py-3 whitespace-nowrap text-gray-500 font-mono text-xs">{log.ip_address || '-'}</td>
                        <td className="px-4 py-3 text-gray-500 max-w-xs truncate">
                          {log.details ? (
                            <details className="cursor-pointer">
                              <summary className="text-primary-600 hover:underline">View</summary>
                              <pre className="mt-2 text-xs bg-gray-50 p-2 rounded border font-mono whitespace-pre-wrap">
                                {JSON.stringify(log.details, null, 2)}
                              </pre>
                            </details>
                          ) : '-'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            {data && data.total > 0 && (
              <div className="border-t border-gray-200 p-4">
                <Pagination page={page} pageSize={pageSize} total={data.total} onPageChange={setPage} onPageSizeChange={setPageSize} />
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
