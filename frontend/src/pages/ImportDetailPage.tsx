import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { 
  getImportBatchDetail, 
  getStagingRecords, 
  commitBatch 
} from '../api/imports';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Pagination } from '../components/ui/Pagination';
import { Check } from 'lucide-react';

export function ImportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const batchId = parseInt(id || '0', 10);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  const { data: batch, isLoading: isLoadingBatch } = useQuery({
    queryKey: ['importBatch', batchId],
    queryFn: () => getImportBatchDetail(batchId),
    enabled: !!batchId,
  });

  const { data: staging } = useQuery({
    queryKey: ['stagingRecords', batchId, page, pageSize],
    queryFn: () => getStagingRecords(batchId, { page, page_size: pageSize }),
    enabled: !!batch && ['COMPLETED', 'COMPLETED_WITH_WARNINGS'].includes(batch.status),
  });

  const commitMutation = useMutation({
    mutationFn: commitBatch,
    onSuccess: (data) => {
      toast.success(`Committed ${data.records_committed} records successfully`);
      queryClient.invalidateQueries({ queryKey: ['importBatch', batchId] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Commit failed');
    }
  });

  if (isLoadingBatch) {
    return <div className="p-8 text-center text-gray-500">Loading...</div>;
  }

  if (!batch) {
    return <div className="p-8 text-center text-red-500">Batch not found</div>;
  }

  const isReadyToCommit = ['COMPLETED', 'COMPLETED_WITH_WARNINGS'].includes(batch.status);
  
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">
            Import Detail: {batch.filename}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {batch.round_name} • {batch.year} • Uploaded {new Date(batch.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge 
            variant={
              batch.status === 'COMMITTED' || batch.status === 'COMPLETED' ? 'success' :
              batch.status === 'FAILED' ? 'error' :
              batch.status === 'COMPLETED_WITH_WARNINGS' ? 'warning' : 'default'
            }
            className="text-sm px-3 py-1"
          >
            {batch.status.replace(/_/g, ' ')}
          </Badge>
          
          {isReadyToCommit && (
            <Button 
              onClick={() => {
                if(window.confirm('Commit these records to production?')) {
                  commitMutation.mutate(batchId);
                }
              }}
              isLoading={commitMutation.isPending}
              className="gap-2"
            >
              <Check className="h-4 w-4" />
              Commit to Production
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="text-sm font-medium text-gray-500 mb-1">Records Created</div>
            <div className="text-3xl font-bold text-gray-900">{batch.records_created}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="text-sm font-medium text-gray-500 mb-1">Pages Processed</div>
            <div className="text-3xl font-bold text-gray-900">{batch.pages_processed}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="text-sm font-medium text-amber-600 mb-1">Warnings</div>
            <div className="text-3xl font-bold text-amber-600">{batch.warning_count}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="text-sm font-medium text-red-600 mb-1">Errors</div>
            <div className="text-3xl font-bold text-red-600">{batch.error_count}</div>
          </CardContent>
        </Card>
      </div>

      {isReadyToCommit && staging && (
        <Card>
          <CardHeader>
            <CardTitle>Staging Records Preview</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">College</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Course</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cat / Stage</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Merit</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Percentile</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {staging.items.map((r) => (
                    <tr key={r.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{r.college_code}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{r.course_code}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {r.category_code} <span className="mx-1 text-gray-300">|</span> {r.stage}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {r.merit_number}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-primary text-right">
                        {r.percentile?.toFixed(7)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={page}
              pageSize={pageSize}
              total={staging.total}
              onPageChange={setPage}
              onPageSizeChange={setPageSize}
            />
          </CardContent>
        </Card>
      )}

      {batch.recent_logs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Logs</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Level</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Message</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Page</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200 text-sm">
                  {batch.recent_logs.map((log) => (
                    <tr key={log.id}>
                      <td className="px-6 py-3 whitespace-nowrap text-gray-500">
                        {new Date(log.created_at).toLocaleTimeString()}
                      </td>
                      <td className="px-6 py-3 whitespace-nowrap">
                        <Badge variant={log.level === 'ERROR' ? 'error' : log.level === 'WARNING' ? 'warning' : 'default'}>
                          {log.level}
                        </Badge>
                      </td>
                      <td className="px-6 py-3 text-gray-900">{log.message}</td>
                      <td className="px-6 py-3 whitespace-nowrap text-right text-gray-500">
                        {log.page_number || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
