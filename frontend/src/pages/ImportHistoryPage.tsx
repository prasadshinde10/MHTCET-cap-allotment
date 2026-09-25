import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { FileUp, Eye, Trash2 } from 'lucide-react';
import { getImportBatches, deleteBatch } from '../api/imports';
import { Button } from '../components/ui/Button';
import { Pagination } from '../components/ui/Pagination';
import { Badge } from '../components/ui/Badge';
import { Select } from '../components/ui/Select';
import { Input } from '../components/ui/Input';

export function ImportHistoryPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [status, setStatus] = useState<string>('');
  const [year, setYear] = useState<string>('');

  const { data, isLoading } = useQuery({
    queryKey: ['importBatches', page, pageSize, status, year],
    queryFn: () => getImportBatches({
      page,
      page_size: pageSize,
      status: status || undefined,
      year: year ? parseInt(year, 10) : undefined
    }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteBatch,
    onSuccess: () => {
      toast.success('Batch deleted');
      queryClient.invalidateQueries({ queryKey: ['importBatches'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to delete batch');
    }
  });

  const statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'PENDING', label: 'Pending' },
    { value: 'PROCESSING', label: 'Processing' },
    { value: 'COMPLETED', label: 'Completed' },
    { value: 'COMPLETED_WITH_WARNINGS', label: 'Completed (Warnings)' },
    { value: 'FAILED', label: 'Failed' },
    { value: 'COMMITTED', label: 'Committed' },
  ];

  const getStatusVariant = (st: string): 'success' | 'warning' | 'error' | 'info' | 'default' => {
    switch (st) {
      case 'PENDING': return 'default';
      case 'PROCESSING': return 'info';
      case 'COMPLETED': return 'success';
      case 'COMPLETED_WITH_WARNINGS': return 'warning';
      case 'FAILED': return 'error';
      case 'COMMITTED': return 'success';
      default: return 'default';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">Import History</h1>
        <Button onClick={() => navigate('/imports/new')} className="gap-2">
          <FileUp className="h-4 w-4" />
          New Import
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 bg-white p-4 rounded-lg shadow-sm border border-gray-100">
        <div className="w-full sm:w-48">
          <Select
            options={statusOptions}
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          />
        </div>
        <div className="w-full sm:w-48">
          <Input
            type="number"
            placeholder="Year (e.g. 2026)"
            value={year}
            onChange={(e) => setYear(e.target.value)}
          />
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">File / Round</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stats</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                    Loading...
                  </td>
                </tr>
              ) : data?.items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                    No import batches found.
                  </td>
                </tr>
              ) : (
                data?.items.map((batch) => (
                  <tr key={batch.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex flex-col">
                        <span className="text-sm font-medium text-gray-900 truncate max-w-xs" title={batch.filename}>
                          {batch.filename}
                        </span>
                        <span className="text-sm text-gray-500">
                          {batch.round_name} • {batch.year}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge variant={getStatusVariant(batch.status)}>
                        {batch.status.replace(/_/g, ' ')}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div>Rec: {batch.records_created}</div>
                      {(batch.error_count > 0 || batch.warning_count > 0) && (
                        <div className="text-red-500 text-xs">
                          {batch.error_count} err, {batch.warning_count} warn
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(batch.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="ghost" size="sm" onClick={() => navigate(`/imports/${batch.id}`)}>
                          <Eye className="h-4 w-4 mr-1" />
                          View
                        </Button>
                        {['PENDING', 'FAILED'].includes(batch.status) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            onClick={() => {
                              if (window.confirm('Delete this import batch?')) {
                                deleteMutation.mutate(batch.id);
                              }
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {data && (
          <Pagination
            page={page}
            pageSize={pageSize}
            total={data.total}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
        )}
      </div>
    </div>
  );
}
