import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  UploadCloud,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Database,
  ArrowRight,
  RefreshCw,
  FileText,
  Award
} from 'lucide-react';
import { FileDropzone } from '../components/ui/FileDropzone';
import { Button } from '../components/ui/Button';
import { Select } from '../components/ui/Select';
import {
  uploadPdf,
  processBatch,
  getDbStatus,
  resetDatabase,
  ProcessBatchResponse
} from '../api/imports';
import {
  getJosaaStats,
  resetJosaaDatabase,
  reloadJosaaData
} from '../api/josaa';

export function ImportNewPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [file, setFile] = useState<File | null>(null);
  const [year, setYear] = useState<number>(2026);
  const [round, setRound] = useState<number>(1);
  const [batchId, setBatchId] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [showJosaaResetConfirm, setShowJosaaResetConfirm] = useState(false);
  const [parseResult, setParseResult] = useState<ProcessBatchResponse | null>(null);

  // Fetch live database statistics
  const { data: dbStatus, refetch: refetchDbStatus, isFetching: isFetchingStats } = useQuery({
    queryKey: ['dbStatus'],
    queryFn: getDbStatus,
    staleTime: 5000,
  });

  // Fetch JoSAA database statistics
  const { data: josaaStats, refetch: refetchJosaaStats, isFetching: isFetchingJosaaStats } = useQuery({
    queryKey: ['josaaStats'],
    queryFn: getJosaaStats,
    staleTime: 5000,
  });

  // Reset JoSAA database mutation
  const resetJosaaMutation = useMutation({
    mutationFn: resetJosaaDatabase,
    onSuccess: (data) => {
      toast.success(data.message || 'JoSAA database wiped successfully!');
      setShowJosaaResetConfirm(false);
      refetchJosaaStats();
      queryClient.invalidateQueries({ queryKey: ['josaaFilterOptions'] });
      queryClient.invalidateQueries({ queryKey: ['josaaCutoffs'] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.message || 'Failed to reset JoSAA database');
    }
  });

  // Reload JoSAA sample/official data mutation
  const reloadJosaaMutation = useMutation({
    mutationFn: reloadJosaaData,
    onSuccess: (data) => {
      toast.success(data.message || 'JoSAA data restored successfully!');
      refetchJosaaStats();
      queryClient.invalidateQueries({ queryKey: ['josaaFilterOptions'] });
      queryClient.invalidateQueries({ queryKey: ['josaaCutoffs'] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.message || 'Failed to reload JoSAA data');
    }
  });

  // Reset database mutation
  const resetMutation = useMutation({
    mutationFn: resetDatabase,
    onSuccess: (data) => {
      toast.success(data.message || 'Database reset successfully!');
      setShowResetConfirm(false);
      setParseResult(null);
      setBatchId(null);
      setFile(null);
      refetchDbStatus();
      queryClient.invalidateQueries({ queryKey: ['cutoffs'] });
      queryClient.invalidateQueries({ queryKey: ['filterOptions'] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.message || 'Failed to reset database');
    }
  });

  // Upload PDF mutation
  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error('Please select a PDF file first');
      return uploadPdf(file, year, round);
    },
    onSuccess: (data) => {
      toast.success('PDF uploaded successfully! Ready to parse.');
      setBatchId(data.import_batch_id);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.message || 'Upload failed');
    }
  });

  // Process batch mutation
  const processMutation = useMutation({
    mutationFn: () => {
      if (!batchId) throw new Error('No batch selected for processing');
      return processBatch(batchId);
    },
    onMutate: () => {
      setIsProcessing(true);
    },
    onSuccess: (data) => {
      toast.success(`Parsing complete! Created ${data.records_created.toLocaleString()} cutoff records.`);
      setIsProcessing(false);
      setParseResult(data);
      refetchDbStatus();
      queryClient.invalidateQueries({ queryKey: ['cutoffs'] });
      queryClient.invalidateQueries({ queryKey: ['filterOptions'] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.message || 'Parsing failed');
      setIsProcessing(false);
    }
  });

  const years = [
    { value: 2026, label: '2026' },
    { value: 2025, label: '2025' },
    { value: 2024, label: '2024' },
    { value: 2027, label: '2027' },
  ];

  const rounds = [
    { value: 1, label: 'CAP Round 1' },
    { value: 2, label: 'CAP Round 2' },
    { value: 3, label: 'CAP Round 3' },
    { value: 4, label: 'CAP Round 4' },
  ];

  const handleStartAnother = () => {
    setParseResult(null);
    setBatchId(null);
    setFile(null);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Page Header */}
      <div className="bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <UploadCloud className="w-5 h-5 text-blue-600" />
            PDF Parser & Data Ingestion
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Upload official MHT-CET CAP Cutoff PDFs to parse and populate the production database in real-time.
          </p>
        </div>
      </div>

      {/* Database Status Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* MHT-CET Database Status */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-blue-50 border border-blue-200/60 flex items-center justify-center text-blue-600">
                <Database className="w-3.5 h-3.5" />
              </div>
              <div>
                <h3 className="text-xs font-bold text-slate-900 tracking-tight">MHT-CET Database</h3>
                <p className="text-[10px] text-slate-400">Maharashtra State & All India CAP</p>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetchDbStatus()}
                disabled={isFetchingStats}
                className="h-7 px-2 text-[11px]"
                title="Refresh stats"
              >
                <RefreshCw className={`w-3 h-3 ${isFetchingStats ? 'animate-spin' : ''}`} />
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => setShowResetConfirm(true)}
                className="h-7 px-2 text-[11px]"
                title="Reset MHT-CET Database"
              >
                <Trash2 className="w-3 h-3 mr-1" />
                Reset DB
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2.5">
            <div className="bg-slate-50/80 rounded-lg p-3 border border-slate-100">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block">Cutoffs</span>
              <span className="font-bold text-base text-slate-900 mt-0.5 block">
                {isFetchingStats ? '...' : (dbStatus?.total_cutoffs ?? 0).toLocaleString()}
              </span>
            </div>
            <div className="bg-slate-50/80 rounded-lg p-3 border border-slate-100">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block">Colleges</span>
              <span className="font-bold text-base text-slate-900 mt-0.5 block">
                {isFetchingStats ? '...' : (dbStatus?.total_colleges ?? 0).toLocaleString()}
              </span>
            </div>
            <div className="bg-slate-50/80 rounded-lg p-3 border border-slate-100">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block">Courses</span>
              <span className="font-bold text-base text-slate-900 mt-0.5 block">
                {isFetchingStats ? '...' : (dbStatus?.total_courses ?? 0).toLocaleString()}
              </span>
            </div>
          </div>
        </div>

        {/* JoSAA Standalone Database Status */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-amber-50 border border-amber-200/60 flex items-center justify-center text-amber-600">
                <Award className="w-3.5 h-3.5" />
              </div>
              <div>
                <h3 className="text-xs font-bold text-slate-900 tracking-tight">JoSAA Standalone DB</h3>
                <p className="text-[10px] text-slate-400">IIT / NIT / IIIT / GFTI (Rounds 1–5)</p>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetchJosaaStats()}
                disabled={isFetchingJosaaStats}
                className="h-7 px-2 text-[11px]"
                title="Refresh stats"
              >
                <RefreshCw className={`w-3 h-3 ${isFetchingJosaaStats ? 'animate-spin' : ''}`} />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => reloadJosaaMutation.mutate()}
                disabled={reloadJosaaMutation.isPending}
                className="h-7 px-2 text-[11px] text-blue-600 border-blue-200 hover:bg-blue-50"
                title="Reload official JoSAA registry"
              >
                <RefreshCw className={`w-3 h-3 mr-1 ${reloadJosaaMutation.isPending ? 'animate-spin' : ''}`} />
                Restore
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => setShowJosaaResetConfirm(true)}
                className="h-7 px-2 text-[11px]"
                title="Wipe JoSAA Database"
              >
                <Trash2 className="w-3 h-3 mr-1" />
                Wipe
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-2">
            <div className="bg-slate-50/80 rounded-lg p-2.5 border border-slate-100">
              <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-400 block truncate">Cutoffs</span>
              <span className="font-bold text-sm text-slate-900 mt-0.5 block truncate">
                {isFetchingJosaaStats ? '...' : (josaaStats?.total_cutoffs ?? 0).toLocaleString()}
              </span>
            </div>
            <div className="bg-slate-50/80 rounded-lg p-2.5 border border-slate-100">
              <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-400 block truncate">Institutes</span>
              <span className="font-bold text-sm text-slate-900 mt-0.5 block truncate">
                {isFetchingJosaaStats ? '...' : (josaaStats?.total_institutes ?? 0).toLocaleString()}
              </span>
            </div>
            <div className="bg-slate-50/80 rounded-lg p-2.5 border border-slate-100">
              <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-400 block truncate">Programs</span>
              <span className="font-bold text-sm text-slate-900 mt-0.5 block truncate">
                {isFetchingJosaaStats ? '...' : (josaaStats?.total_programs ?? 0).toLocaleString()}
              </span>
            </div>
            <div className="bg-slate-50/80 rounded-lg p-2.5 border border-slate-100">
              <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-400 block truncate">Categories</span>
              <span className="font-bold text-sm text-slate-900 mt-0.5 block truncate">
                {isFetchingJosaaStats ? '...' : (josaaStats?.total_categories ?? 0).toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Modal for Wiping JoSAA Database */}
      {showJosaaResetConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-5 space-y-4 border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-rose-50 border border-rose-200/80 flex items-center justify-center flex-shrink-0 text-rose-600">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-sm">Wipe JoSAA Database Records?</h3>
                <p className="text-[11px] text-slate-500">This clears all JoSAA cutoffs, institutes, and academic programs.</p>
              </div>
            </div>
            <div className="text-xs text-slate-600 bg-amber-50/80 border border-amber-200/80 rounded-lg p-3 space-y-1">
              <p className="font-semibold text-amber-900">Segregation Notes:</p>
              <p>• Only the independent <span className="font-mono text-amber-950">josaa.db</span> database is wiped.</p>
              <p>• MHT-CET database records and administrator credentials remain completely untouched.</p>
              <p>• You can click "Restore" at any time to re-populate the official dataset.</p>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowJosaaResetConfirm(false)}
                disabled={resetJosaaMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => resetJosaaMutation.mutate()}
                isLoading={resetJosaaMutation.isPending}
              >
                Yes, Wipe JoSAA Data
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal for Resetting MHT-CET Database */}
      {showResetConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-5 space-y-4 border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-rose-50 border border-rose-200/80 flex items-center justify-center flex-shrink-0 text-rose-600">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-sm">Clear MHT-CET Database Records?</h3>
                <p className="text-[11px] text-slate-500">This will wipe cutoffs, colleges, courses, and All-India records.</p>
              </div>
            </div>
            <div className="text-xs text-slate-600 bg-amber-50/80 border border-amber-200/80 rounded-lg p-3 space-y-1">
              <p className="font-semibold text-amber-900">Safety Safeguards Active:</p>
              <p>• Administrator accounts and login credentials remain completely safe.</p>
              <p>• Master institute directory will be retained for standalone ingestion.</p>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowResetConfirm(false)}
                disabled={resetMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => resetMutation.mutate()}
                isLoading={resetMutation.isPending}
              >
                Yes, Clear Database
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Parsing Complete Results Card */}
      {parseResult && (
        <div className="bg-white rounded-xl shadow-xs border border-emerald-200 p-6 space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200/80 flex items-center justify-center text-emerald-600 flex-shrink-0">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-slate-900 tracking-tight">PDF Ingestion Completed Successfully!</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                The PyMuPDF coordinate parser has extracted and populated the database with real-time cutoff records.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-emerald-50/40 rounded-lg p-3.5 border border-emerald-100">
            <div>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block">Pages Processed</span>
              <span className="text-lg font-bold text-slate-900 mt-0.5 block">{parseResult.pages_processed}</span>
            </div>
            <div>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block">Records Created</span>
              <span className="text-lg font-bold text-emerald-700 mt-0.5 block">{parseResult.records_created.toLocaleString()}</span>
            </div>
            <div>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block">Colleges Found</span>
              <span className="text-lg font-bold text-sky-700 mt-0.5 block">{parseResult.colleges_found ?? 'N/A'}</span>
            </div>
            <div>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block">Courses Found</span>
              <span className="text-lg font-bold text-indigo-700 mt-0.5 block">{parseResult.courses_found ?? 'N/A'}</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
            <Button
              variant="outline"
              size="sm"
              onClick={handleStartAnother}
            >
              Parse Another PDF
            </Button>
            <Button
              size="sm"
              onClick={() => navigate('/search')}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              Inspect In Cutoff Search
              <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
            </Button>
          </div>
        </div>
      )}

      {/* Upload and Parse Workflow: Step 1 */}
      {!parseResult && !batchId && (
        <div className="bg-white rounded-xl shadow-xs border border-slate-200/90 p-5 sm:p-6 space-y-5">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="font-bold text-slate-900 text-sm tracking-tight">Step 1: Select CAP Round & Upload PDF</h2>
            <p className="text-xs text-slate-500 mt-0.5">Configure target admission year and upload the official state or All India cutoff PDF.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Select
              label="Admission Year"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              options={years}
            />
            <Select
              label="CAP Round"
              value={round}
              onChange={(e) => setRound(Number(e.target.value))}
              options={rounds}
            />
          </div>

          <div>
            <FileDropzone onFileSelect={setFile} />
          </div>

          <div className="flex justify-end pt-2 border-t border-slate-100">
            <Button
              onClick={() => uploadMutation.mutate()}
              isLoading={uploadMutation.isPending}
              disabled={!file}
              size="md"
            >
              <UploadCloud className="w-4 h-4 mr-1.5" />
              Upload PDF
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Processing in progress or ready */}
      {!parseResult && batchId && (
        <div className="bg-white rounded-xl shadow-xs border border-slate-200/90 p-8 space-y-5 text-center">
          <div className="mx-auto w-12 h-12 rounded-xl bg-blue-50 border border-blue-200/60 flex items-center justify-center text-blue-600">
            <FileText className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-900 tracking-tight">
              {isProcessing ? 'Parsing PDF in Real-Time...' : 'PDF Ready to Parse'}
            </h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              {isProcessing
                ? 'Extracting table matrices, college metadata, categories, ranks, and percentiles using PyMuPDF. Please keep this window open...'
                : `Uploaded for Admission Year ${year}, CAP Round ${round}. Click below to execute extraction.`}
            </p>
          </div>

          {isProcessing && (
            <div className="flex flex-col items-center justify-center py-4 space-y-2">
              <RefreshCw className="w-6 h-6 text-blue-600 animate-spin" />
              <div className="text-xs text-slate-600 font-medium">Processing pages and committing cutoff batches...</div>
            </div>
          )}

          <div className="flex justify-center gap-2.5 pt-2 border-t border-slate-100">
            {!isProcessing && (
              <Button
                variant="outline"
                size="md"
                onClick={() => setBatchId(null)}
              >
                Cancel / Choose Another File
              </Button>
            )}
            <Button
              onClick={() => processMutation.mutate()}
              isLoading={isProcessing}
              size="md"
            >
              {isProcessing ? 'Parsing In Progress...' : 'Start Real-Time Parsing'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export default ImportNewPage;
