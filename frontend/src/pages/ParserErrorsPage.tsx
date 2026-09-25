import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getParserErrors, updateParserError, ParserError } from '../api/parserErrors';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Modal from '../components/ui/Modal';
import Spinner from '../components/ui/Spinner';
import Select from '../components/ui/Select';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import Pagination from '../components/ui/Pagination';
import toast from 'react-hot-toast';

export function ParserErrorsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [status, setStatus] = useState('');
  const [severity, setSeverity] = useState('');
  
  const [selectedError, setSelectedError] = useState<ParserError | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [updateStatus, setUpdateStatus] = useState('');
  const [notes, setNotes] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['parser-errors', page, pageSize, status, severity],
    queryFn: () => getParserErrors({ page, page_size: pageSize, status: status || undefined, severity: severity || undefined }),
  });

  const mutation = useMutation({
    mutationFn: () => updateParserError(selectedError!.id, { status: updateStatus, resolution_notes: notes }),
    onSuccess: () => {
      toast.success('Error status updated successfully');
      setModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ['parser-errors'] });
    },
    onError: () => toast.error('Failed to update parser error'),
  });

  const handleRowClick = (error: ParserError) => {
    setSelectedError(error);
    setUpdateStatus(error.status);
    setNotes('');
    setModalOpen(true);
  };

  const getSeverityBadge = (sev: string): 'error' | 'warning' | 'info' | 'default' => {
    switch (sev) {
      case 'CRITICAL': return 'error';
      case 'ERROR': return 'error';
      case 'WARNING': return 'warning';
      case 'INFO': return 'info';
      default: return 'default';
    }
  };

  const errorItems = data?.items || [];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Parser Errors</h1>

      <Card className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Select
            label="Severity"
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            options={[
              { value: '', label: 'All Severities' },
              { value: 'CRITICAL', label: 'Critical' },
              { value: 'ERROR', label: 'Error' },
              { value: 'WARNING', label: 'Warning' },
              { value: 'INFO', label: 'Info' }
            ]}
          />
          <Select
            label="Status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            options={[
              { value: '', label: 'All Statuses' },
              { value: 'OPEN', label: 'Open' },
              { value: 'ACKNOWLEDGED', label: 'Acknowledged' },
              { value: 'RESOLVED', label: 'Resolved' }
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
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Page</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Severity</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Message</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200 text-sm">
                  {errorItems.length === 0 ? (
                    <tr><td colSpan={6} className="px-6 py-8 text-center text-sm text-gray-500">No parser errors recorded.</td></tr>
                  ) : (
                    errorItems.map((err) => (
                      <tr key={err.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => handleRowClick(err)}>
                        <td className="px-4 py-3 whitespace-nowrap text-gray-500">{err.source_page || '-'}</td>
                        <td className="px-4 py-3 whitespace-nowrap font-medium text-gray-900">{err.error_type}</td>
                        <td className="px-4 py-3 whitespace-nowrap"><Badge variant={getSeverityBadge(err.severity)}>{err.severity}</Badge></td>
                        <td className="px-4 py-3 text-gray-600 truncate max-w-sm">{err.error_message}</td>
                        <td className="px-4 py-3 whitespace-nowrap text-gray-500">{err.status}</td>
                        <td className="px-4 py-3 whitespace-nowrap text-right">
                          <Button variant="secondary" size="sm" onClick={(e) => { e.stopPropagation(); handleRowClick(err); }}>
                            Review
                          </Button>
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

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Parser Error Details">
        {selectedError && (
          <div className="space-y-4 text-sm">
            <div>
              <p className="font-semibold text-gray-700">Error Type: {selectedError.error_type}</p>
              <p className="text-gray-900 mt-1">{selectedError.error_message}</p>
            </div>
            {selectedError.raw_text && (
              <div>
                <p className="font-semibold text-gray-700 mb-1">Raw Text Context:</p>
                <pre className="bg-gray-50 p-2.5 rounded border border-gray-200 text-xs overflow-x-auto whitespace-pre-wrap font-mono">
                  {selectedError.raw_text}
                </pre>
              </div>
            )}
            <div className="pt-2 border-t border-gray-200 space-y-3">
              <Select
                label="Update Status"
                value={updateStatus}
                onChange={(e) => setUpdateStatus(e.target.value)}
                options={[
                  { value: 'OPEN', label: 'Open' },
                  { value: 'ACKNOWLEDGED', label: 'Acknowledged' },
                  { value: 'RESOLVED', label: 'Resolved' }
                ]}
              />
              <Input
                label="Resolution Notes"
                placeholder="Optional notes regarding the error resolution"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
            <div className="flex justify-end space-x-2 pt-2">
              <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
              <Button onClick={() => mutation.mutate()} isLoading={mutation.isPending}>Save</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
