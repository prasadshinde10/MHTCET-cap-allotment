import React, { useState, useEffect } from 'react';
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
  Building,
  GraduationCap,
  Award,
  Globe,
  Sparkles
} from 'lucide-react';
import { FileDropzone } from '../components/ui/FileDropzone';
import { Button } from '../components/ui/Button';
import { Select } from '../components/ui/Select';
import {
  uploadPdf,
  processBatch,
  getDbStatus,
  resetDatabase,
  restoreOfficialCutoffs,
  getImportBatchDetail,
  startInstituteScraper,
  getInstituteScraperProgress,
  ProcessBatchResponse
} from '../api/imports';
import {
  getJosaaStats,
  resetJosaaDatabase,
  reloadJosaaData,
  scrapeJosaaData,
  getJosaaScraperStatus,
  JosaaScraperStatus
} from '../api/josaa';

export function ImportNewPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [file, setFile] = useState<File | null>(null);
  const [year, setYear] = useState<number>(2026);
  const [round, setRound] = useState<number>(0);
  const [batchId, setBatchId] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [showRestoreConfirm, setShowRestoreConfirm] = useState(false);
  const [showJosaaResetConfirm, setShowJosaaResetConfirm] = useState(false);
  const [parseResult, setParseResult] = useState<ProcessBatchResponse | null>(null);

  // Poll real-time progress during PDF extraction
  const { data: batchProgress } = useQuery({
    queryKey: ['importProgress', batchId],
    queryFn: () => getImportBatchDetail(batchId!),
    enabled: !!batchId && isProcessing,
    refetchInterval: isProcessing ? 800 : false,
  });

  const totalPages = batchProgress?.total_pages || 0;
  const pagesProcessed = batchProgress?.pages_processed || 0;
  const recordsCreated = batchProgress?.records_created || 0;

  const progressPercent = totalPages > 0
    ? Math.min(100, Math.round((pagesProcessed / totalPages) * 100))
    : (isProcessing ? 4 : 0);

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
      toast.success(data.message || 'JoSAA web scraping started!');
      setIsJosaaScrapingActive(true);
      refetchJosaaScraperProgress();
      queryClient.invalidateQueries({ queryKey: ['josaaScraperProgress'] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.message || 'Failed to start JoSAA scraper');
    }
  });

  // Poll real-time progress for JoSAA Multi-Year Web Scraper
  const [isJosaaScrapingActive, setIsJosaaScrapingActive] = useState(false);

  const { data: josaaScraperProgress, refetch: refetchJosaaScraperProgress } = useQuery<JosaaScraperStatus>({
    queryKey: ['josaaScraperProgress'],
    queryFn: getJosaaScraperStatus,
    refetchInterval: isJosaaScrapingActive ? 1000 : 3000,
  });

  useEffect(() => {
    if (josaaScraperProgress?.is_running) {
      setIsJosaaScrapingActive(true);
    } else if (isJosaaScrapingActive && josaaScraperProgress && !josaaScraperProgress.is_running) {
      setIsJosaaScrapingActive(false);
      if (josaaScraperProgress.status === 'COMPLETED') {
        toast.success(josaaScraperProgress.message || 'JoSAA cutoffs for Years 2025 & 2026 scraped and ingested successfully!');
        refetchJosaaStats();
        queryClient.invalidateQueries({ queryKey: ['josaaFilterOptions'] });
        queryClient.invalidateQueries({ queryKey: ['josaaCutoffs'] });
      } else if (josaaScraperProgress.status === 'FAILED') {
        toast.error(`JoSAA scraping failed: ${josaaScraperProgress.error || 'Check server connection'}`);
      }
    }
  }, [josaaScraperProgress?.is_running, josaaScraperProgress?.status]);

  const startJosaaScraperMutation = useMutation({
    mutationFn: scrapeJosaaData,
    onSuccess: (data) => {
      setIsJosaaScrapingActive(true);
      toast.success(data.message || 'JoSAA Multi-Year Web Scraper started in background!');
      refetchJosaaScraperProgress();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.message || 'Failed to start JoSAA scraper');
    }
  });

  // Poll real-time progress for MHT-CET Institute Web Scraper
  const [isScrapingActive, setIsScrapingActive] = useState(false);

  const { data: scraperProgress, refetch: refetchScraperProgress } = useQuery({
    queryKey: ['instituteScraperProgress'],
    queryFn: getInstituteScraperProgress,
    refetchInterval: isScrapingActive ? 800 : 3000,
  });

  useEffect(() => {
    if (scraperProgress?.is_running) {
      setIsScrapingActive(true);
    } else if (isScrapingActive && scraperProgress && !scraperProgress.is_running) {
      setIsScrapingActive(false);
      if (scraperProgress.status === 'COMPLETED') {
        toast.success(scraperProgress.message || 'MHT-CET institute scraping completed!');
        refetchDbStatus();
        queryClient.invalidateQueries({ queryKey: ['filterOptions'] });
      } else if (scraperProgress.status === 'FAILED') {
        toast.error(scraperProgress.error || 'Scraper failed');
      }
    }
  }, [scraperProgress?.is_running, scraperProgress?.status]);

  const startScraperMutation = useMutation({
    mutationFn: startInstituteScraper,
    onSuccess: (data) => {
      setIsScrapingActive(true);
      toast.success(data.message || 'MHT-CET Web Scraper started!');
      refetchScraperProgress();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.message || 'Failed to start MHT-CET scraper');
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

  // Restore complete verified official cutoffs mutation
  const restoreCutoffsMutation = useMutation({
    mutationFn: restoreOfficialCutoffs,
    onSuccess: (data) => {
      toast.success(data.message || '111,560 cutoffs restored successfully!');
      setShowRestoreConfirm(false);
      refetchDbStatus();
      queryClient.invalidateQueries({ queryKey: ['cutoffs'] });
      queryClient.invalidateQueries({ queryKey: ['filterOptions'] });
      queryClient.invalidateQueries({ queryKey: ['dbStatus'] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.message || 'Failed to restore cutoffs');
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
    { value: 0, label: 'Auto-detect by Parsing PDF (Recommended)' },
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
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <UploadCloud className="w-7 h-7 text-primary-600" />
            PDF Parser & Real-Time Data Ingestion
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Upload official MHT-CET CAP Cutoff PDFs and extract real-time cutoff records into the database.
          </p>
        </div>
      </div>

      {/* Database Status & Clean Slate Control */}
      <div className="bg-slate-900 text-white rounded-xl shadow-md p-5 border border-slate-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              <Database className="w-4 h-4 text-primary-400" />
              Active Database Records
            </div>
            <div className="mt-3 flex flex-wrap gap-4 text-sm">
              <div className="bg-slate-800 px-3.5 py-2 rounded-lg border border-slate-700/60">
                <span className="text-slate-400 block text-xs">Total Cutoffs</span>
                <span className="font-bold text-lg text-emerald-400">
                  {isFetchingStats ? '...' : (dbStatus?.total_cutoffs ?? 0).toLocaleString()}
                </span>
              </div>
              <div className="bg-slate-800 px-3.5 py-2 rounded-lg border border-slate-700/60">
                <span className="text-slate-400 block text-xs">Colleges</span>
                <span className="font-bold text-lg text-sky-400">
                  {isFetchingStats ? '...' : (dbStatus?.total_colleges ?? 0).toLocaleString()}
                </span>
              </div>
              <div className="bg-slate-800 px-3.5 py-2 rounded-lg border border-slate-700/60">
                <span className="text-slate-400 block text-xs">Courses</span>
                <span className="font-bold text-lg text-indigo-400">
                  {isFetchingStats ? '...' : (dbStatus?.total_courses ?? 0).toLocaleString()}
                </span>
              </div>
              <div className="bg-slate-800 px-3.5 py-2 rounded-lg border border-slate-700/60">
                <span className="text-slate-400 block text-xs">DTE Institutes</span>
                <span className="font-bold text-lg text-amber-400">
                  {isFetchingStats ? '...' : (dbStatus?.total_institutes ?? 0).toLocaleString()}
                </span>
              </div>
              <div className="bg-slate-800 px-3.5 py-2 rounded-lg border border-slate-700/60">
                <span className="text-slate-400 block text-xs">Choice Intake</span>
                <span className="font-bold text-lg text-teal-400">
                  {isFetchingStats ? '...' : (dbStatus?.total_institute_courses ?? 0).toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-center flex-wrap">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchDbStatus()}
              disabled={isFetchingStats}
              className="text-slate-300 border-slate-700 hover:bg-slate-800"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isFetchingStats ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button
              size="sm"
              onClick={() => setShowRestoreConfirm(true)}
              disabled={restoreCutoffsMutation.isPending}
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-3.5 shadow-sm shadow-emerald-900/30"
              title="Restore all 111,560 verified cutoffs across all 4 CAP rounds (State & All India)"
            >
              <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
              Restore Official Cutoffs (111,560 Records)
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => setShowResetConfirm(true)}
              className="bg-red-600/90 hover:bg-red-700 text-white text-xs"
            >
              <Trash2 className="w-3.5 h-3.5 mr-1.5" />
              Clear / Reset Database (100%)
            </Button>
          </div>
        </div>

        {/* Warning Banner if Cutoffs Database is incomplete or empty */}
        {dbStatus && dbStatus.total_cutoffs < 110000 && (
          <div className="mt-4 bg-amber-950/40 border border-amber-500/40 rounded-xl p-3 text-xs text-amber-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-inner">
            <div className="flex items-center gap-2.5">
              <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
              <div>
                <p className="font-semibold text-amber-100">
                  {dbStatus.total_cutoffs === 0
                    ? 'Database is currently empty (0 records).'
                    : `Database is currently partial (${dbStatus.total_cutoffs.toLocaleString()} of 111,560 records).`}
                </p>
                <p className="text-amber-200/80 text-[11px] mt-0.5">
                  To load the full verified MHT-CET dataset (all 4 CAP rounds for both State & All-India), click <strong>"Restore Official Cutoffs"</strong>.
                </p>
              </div>
            </div>
            <Button
              size="sm"
              onClick={() => setShowRestoreConfirm(true)}
              disabled={restoreCutoffsMutation.isPending}
              className="bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs shrink-0"
            >
              Restore 111,560 Cutoffs
            </Button>
          </div>
        )}
      </div>

      {/* MHT-CET Institute Directory Web Scraper Card with Real-Time Progress Bar */}
      <div className="bg-slate-900 text-white rounded-xl shadow-md p-5 border border-emerald-950/80 bg-gradient-to-r from-slate-900 via-emerald-950/30 to-slate-900">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                <Globe className="w-4 h-4 text-emerald-400" />
                MHT-CET Official Institute Directory Web Scraper
              </div>
              <p className="text-xs text-slate-400 mt-1 max-w-xl">
                Extracts all 387 engineering colleges, affiliated universities, minority status, and 4,300+ branchwise intake records directly from the CET portal (<span className="font-mono text-slate-300">fe2026.mahacet.org</span>).
              </p>
            </div>

            <div className="flex items-center gap-2 self-start sm:self-center flex-wrap">
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetchScraperProgress()}
                disabled={isScrapingActive}
                className="text-slate-300 border-slate-700 hover:bg-slate-800"
              >
                <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isScrapingActive ? 'animate-spin' : ''}`} />
                Check Status
              </Button>
              <Button
                size="sm"
                onClick={() => startScraperMutation.mutate()}
                disabled={isScrapingActive || startScraperMutation.isPending}
                className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-4"
              >
                <Globe className={`w-3.5 h-3.5 mr-1.5 ${isScrapingActive ? 'animate-spin' : ''}`} />
                {isScrapingActive ? 'Scraping in Progress...' : 'Run MHT-CET Web Scraper'}
              </Button>
            </div>
          </div>

          {/* Real-time Progress Bar for MHT-CET Scraper */}
          {isScrapingActive && scraperProgress && (
            <div className="bg-slate-800/90 rounded-xl p-4 border border-emerald-800/60 space-y-3 shadow-inner">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 font-medium text-emerald-400">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                  </span>
                  Live Web Scraper Running
                </div>
                <span className="font-semibold text-slate-200">
                  {scraperProgress.progress_percent}% Complete ({scraperProgress.current} / {scraperProgress.total || 387} Institutes)
                </span>
              </div>

              {/* Progress Bar Container */}
              <div className="w-full bg-slate-900 rounded-full h-4 overflow-hidden border border-slate-700 relative shadow-inner">
                <div
                  className="bg-gradient-to-r from-emerald-500 via-teal-500 to-sky-400 h-full transition-all duration-300 ease-out flex items-center justify-end pr-2 text-[10px] font-bold text-white shadow-sm"
                  style={{ width: `${Math.max(scraperProgress.progress_percent, 4)}%` }}
                >
                  {scraperProgress.progress_percent >= 10 && `${scraperProgress.progress_percent}%`}
                </div>
              </div>

              {/* Status and Active Detail */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs text-slate-300 pt-1">
                <div className="flex items-center gap-2 truncate">
                  <RefreshCw className="w-3.5 h-3.5 text-emerald-400 animate-spin flex-shrink-0" />
                  <span className="truncate">{scraperProgress.message}</span>
                </div>
                <div className="flex items-center gap-4 text-xs font-mono shrink-0">
                  <span className="text-emerald-400">{scraperProgress.institutes_created} institutes</span>
                  <span className="text-teal-400">{scraperProgress.courses_created} choice codes</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* JoSAA Standalone Database Status & Wipe Control */}
      <div className="bg-slate-900 text-white rounded-xl shadow-md p-5 border border-indigo-950/80 bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-indigo-400 uppercase tracking-wider">
              <Award className="w-4 h-4 text-amber-400" />
              JoSAA Independent Database (IIT / NIT / IIIT / GFTI)
            </div>
            <div className="mt-3 flex flex-wrap gap-4 text-sm">
              <div className="bg-slate-800 px-3.5 py-2 rounded-lg border border-slate-700/60">
                <span className="text-slate-400 block text-xs">JoSAA Cutoffs</span>
                <span className="font-bold text-lg text-emerald-400">
                  {isFetchingJosaaStats ? '...' : (josaaStats?.total_cutoffs ?? 0).toLocaleString()}
                </span>
              </div>
              <div className="bg-slate-800 px-3.5 py-2 rounded-lg border border-slate-700/60">
                <span className="text-slate-400 block text-xs">Institutes</span>
                <span className="font-bold text-lg text-amber-400">
                  {isFetchingJosaaStats ? '...' : (josaaStats?.total_institutes ?? 0).toLocaleString()}
                </span>
              </div>
              <div className="bg-slate-800 px-3.5 py-2 rounded-lg border border-slate-700/60">
                <span className="text-slate-400 block text-xs">Academic Programs</span>
                <span className="font-bold text-lg text-indigo-400">
                  {isFetchingJosaaStats ? '...' : (josaaStats?.total_programs ?? 0).toLocaleString()}
                </span>
              </div>
              <div className="bg-slate-800 px-3.5 py-2 rounded-lg border border-slate-700/60">
                <span className="text-slate-400 block text-xs">Categories</span>
                <span className="font-bold text-lg text-sky-400">
                  {isFetchingJosaaStats ? '...' : (josaaStats?.total_categories ?? 0).toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-center flex-wrap">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchJosaaScraperProgress()}
              disabled={isJosaaScrapingActive}
              className="text-slate-300 border-slate-700 hover:bg-slate-800 text-xs"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isJosaaScrapingActive ? 'animate-spin' : ''}`} />
              Check Status
            </Button>
            <Button
              size="sm"
              onClick={() => startJosaaScraperMutation.mutate()}
              disabled={isJosaaScrapingActive || startJosaaScraperMutation.isPending}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-4 shadow-sm shadow-indigo-900/40"
            >
              <Globe className={`w-3.5 h-3.5 mr-1.5 ${isJosaaScrapingActive ? 'animate-spin' : ''}`} />
              {isJosaaScrapingActive ? 'Scraping JoSAA (2025 & 2026)...' : 'Run JoSAA Web Scraper (2025 & 2026)'}
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => setShowJosaaResetConfirm(true)}
              className="bg-red-600/90 hover:bg-red-700 text-white text-xs"
            >
              <Trash2 className="w-3.5 h-3.5 mr-1.5" />
              Wipe JoSAA Database
            </Button>
          </div>
        </div>

        {/* Real-time Progress Bar for JoSAA Scraper */}
        {isJosaaScrapingActive && josaaScraperProgress && (
          <div className="mt-4 bg-slate-800/90 rounded-xl p-4 border border-indigo-800/60 space-y-3 shadow-inner">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 font-medium text-indigo-400">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500"></span>
                </span>
                <span>JoSAA Multi-Year Web Scraper Running</span>
                {josaaScraperProgress.current_year && (
                  <span className="text-[11px] font-bold text-amber-300 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800/60">
                    Year {josaaScraperProgress.current_year} • Round {josaaScraperProgress.current_round} of {josaaScraperProgress.current_year === 2025 ? 6 : 5}
                  </span>
                )}
              </div>
              <span className="font-semibold text-slate-200">
                {josaaScraperProgress.progress_percent}% Complete ({josaaScraperProgress.completed_rounds} / {josaaScraperProgress.total_rounds || 11} Rounds)
              </span>
            </div>

            {/* Progress Bar Container */}
            <div className="w-full bg-slate-900 rounded-full h-4 overflow-hidden border border-slate-700 relative shadow-inner">
              <div
                className="bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-400 h-full transition-all duration-300 ease-out flex items-center justify-end pr-2 text-[10px] font-bold text-white shadow-sm"
                style={{ width: `${Math.max(josaaScraperProgress.progress_percent, 4)}%` }}
              >
                {josaaScraperProgress.progress_percent >= 10 && `${josaaScraperProgress.progress_percent}%`}
              </div>
            </div>

            {/* Status and Active Detail */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs text-slate-300 pt-1">
              <div className="flex items-center gap-2 truncate">
                <RefreshCw className="w-3.5 h-3.5 text-indigo-400 animate-spin flex-shrink-0" />
                <span className="truncate">{josaaScraperProgress.message}</span>
              </div>
              <div className="flex items-center gap-4 text-xs font-mono shrink-0">
                <span className="text-indigo-400">{josaaScraperProgress.records_2025.toLocaleString()} (2025)</span>
                <span className="text-purple-400">{josaaScraperProgress.records_2026.toLocaleString()} (2026)</span>
                <span className="text-emerald-400 font-bold">{josaaScraperProgress.total_records.toLocaleString()} total</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Confirmation Modal for Wiping JoSAA Database */}
      {showJosaaResetConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 space-y-4 border border-red-100">
            <div className="flex items-center gap-3 text-red-600">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 className="font-bold text-gray-900 text-base">Wipe JoSAA Database Records?</h3>
                <p className="text-xs text-red-600 font-medium">This will clear all JoSAA cutoff records, institutes, and programs.</p>
              </div>
            </div>
            <div className="text-xs text-gray-600 bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-1">
              <p className="font-semibold text-amber-900">Important Notes:</p>
              <p>1. Only the independent <span className="font-mono">josaa.db</span> file will be wiped.</p>
              <p>2. Your MHT-CET database (<span className="font-mono">cutoff.db</span>) and admin credentials remain completely untouched.</p>
              <p>3. You can click "Reload Official Registry" anytime to restore the 46+ institutes and seed cutoffs.</p>
            </div>
            <div className="flex justify-end gap-2 pt-2">
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
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                Yes, Wipe JoSAA Data
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal for Resetting Database */}
      {showResetConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 space-y-4 border border-red-100">
            <div className="flex items-center gap-3 text-red-600">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 className="font-bold text-gray-900 text-base">Clear All Database Records (100% Wipe)?</h3>
                <p className="text-xs text-red-600 font-medium">
                  This will completely clear 100% of cutoffs, colleges, courses, institutes, and intake tables.
                </p>
              </div>
            </div>
            <div className="text-xs text-gray-600 bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-1.5">
              <p className="font-semibold text-amber-900">Safety Safeguards & Details:</p>
              <p>1. An automatic backup of your current database will be archived in <span className="font-mono">storage/backups</span>.</p>
              <p>2. Your admin account credentials (<span className="font-mono">admin</span> / <span className="font-mono">admin123</span>) will remain untouched.</p>
              <p>3. Both <span className="font-mono">institutes</span> (387) and <span className="font-mono">institute_courses</span> (4,331) tables will be 100% emptied.</p>
              <p>4. You can restore the full verified 111,560 records anytime using the <strong>"Restore Official Cutoffs"</strong> button above.</p>
            </div>
            <div className="flex justify-end gap-2 pt-2">
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
                className="bg-red-600 hover:bg-red-700 text-white font-semibold"
              >
                Yes, Clear 100% Database
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal for Restoring Official Dataset */}
      {showRestoreConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 space-y-4 border border-emerald-100">
            <div className="flex items-center gap-3 text-emerald-600">
              <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <h3 className="font-bold text-gray-900 text-base">Restore All Official CAP Cutoffs?</h3>
                <p className="text-xs text-emerald-700 font-medium">
                  Restores 111,560 verified cutoffs across all 4 CAP Rounds.
                </p>
              </div>
            </div>
            <div className="text-xs text-gray-600 bg-emerald-50/70 border border-emerald-200 rounded-lg p-3 space-y-1.5">
              <p className="font-semibold text-emerald-950">Verified Dataset Summary:</p>
              <p>• <strong>Round 1:</strong> 38,009 cutoffs (36,005 State + 2,004 All India)</p>
              <p>• <strong>Round 2:</strong> 36,143 cutoffs (34,390 State + 1,753 All India)</p>
              <p>• <strong>Round 3:</strong> 21,309 cutoffs (19,837 State + 1,472 All India)</p>
              <p>• <strong>Round 4:</strong> 16,099 cutoffs (14,764 State + 1,335 All India)</p>
              <p>• <strong>Directories:</strong> 387 colleges, 2,332 courses, 387 institutes & 4,331 choice codes.</p>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowRestoreConfirm(false)}
                disabled={restoreCutoffsMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => restoreCutoffsMutation.mutate()}
                isLoading={restoreCutoffsMutation.isPending}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
              >
                Yes, Restore 111,560 Records
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Parsing Complete Results Card */}
      {parseResult && (
        <div className="bg-white rounded-xl shadow-sm border border-emerald-200 p-6 space-y-5">
          <div className="flex items-center gap-3 text-emerald-700">
            <CheckCircle2 className="w-8 h-8 text-emerald-600 flex-shrink-0" />
            <div>
              <h3 className="font-bold text-lg text-gray-900">PDF Ingestion Completed Successfully!</h3>
              <p className="text-sm text-gray-600">
                The PyMuPDF grid parser has extracted and populated the database with real-time cutoff records.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-emerald-50/60 rounded-lg p-4 border border-emerald-100">
            <div>
              <span className="text-xs text-gray-500 block">Pages Processed</span>
              <span className="text-xl font-bold text-gray-900">{parseResult.pages_processed}</span>
            </div>
            <div>
              <span className="text-xs text-gray-500 block">Records Created</span>
              <span className="text-xl font-bold text-emerald-700">{parseResult.records_created.toLocaleString()}</span>
            </div>
            <div>
              <span className="text-xs text-gray-500 block">Colleges Found</span>
              <span className="text-xl font-bold text-sky-700">{parseResult.colleges_found ?? 'N/A'}</span>
            </div>
            <div>
              <span className="text-xs text-gray-500 block">Courses Found</span>
              <span className="text-xl font-bold text-indigo-700">{parseResult.courses_found ?? 'N/A'}</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleStartAnother}
            >
              Parse Another PDF
            </Button>
            <Button
              onClick={() => navigate('/search')}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              Inspect In Cutoff Search
              <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>
          </div>
        </div>
      )}

      {/* Upload and Parse Workflow */}
      {!parseResult && !batchId && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-6">
          <div className="border-b border-gray-100 pb-3">
            <h2 className="font-semibold text-gray-900 text-base">Step 1: Select CAP Round & Upload PDF</h2>
            <p className="text-xs text-gray-500">Configure target admission year and upload the official PDF cutoff sheet.</p>
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
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Cutoff PDF File
            </label>
            <FileDropzone onFileSelect={setFile} />
          </div>

          {/* Informational tip about content-based parsing */}
          <div className="bg-sky-50 border border-sky-200 rounded-lg p-3.5 flex items-start gap-3 text-sky-900">
            <Sparkles className="w-5 h-5 text-sky-600 flex-shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <p className="font-semibold text-sky-950">
                PDF Content Parsing & Automatic Round Detection
              </p>
              <p className="text-sky-800">
                You can upload PDF files with any name (even unlabelled or renamed files). When <strong>"Auto-detect by Parsing PDF"</strong> is selected, the parser extracts the CAP Round directly from the official document header.
              </p>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <Button
              onClick={() => uploadMutation.mutate()}
              isLoading={uploadMutation.isPending}
              disabled={!file}
              size="lg"
              className="bg-primary-600 hover:bg-primary-700 text-white font-medium"
            >
              <UploadCloud className="w-4 h-4 mr-2" />
              Upload PDF
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Processing in progress or ready */}
      {!parseResult && batchId && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 space-y-6 text-center">
          <div className="mx-auto w-14 h-14 rounded-full bg-primary-50 flex items-center justify-center text-primary-600">
            <FileText className="w-7 h-7" />
          </div>
          <div className="space-y-2">
            <h3 className="text-xl font-bold text-gray-900">
              {isProcessing ? 'Parsing PDF & Ingesting Cutoff Data...' : 'PDF Ready to Parse'}
            </h3>
            <p className="text-sm text-gray-500 max-w-md mx-auto">
              {isProcessing
                ? 'Extracting table matrices, college metadata, categories, ranks, and percentiles using PyMuPDF.'
                : `Uploaded for Admission Year ${year}, CAP Round ${round}. Click below to execute extraction.`}
            </p>
          </div>

          {/* Real-time Progress Bar & Statistics */}
          {isProcessing && (
            <div className="bg-slate-900 text-white rounded-xl p-6 border border-slate-800 space-y-4 text-left max-w-2xl mx-auto shadow-lg">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 font-medium text-emerald-400">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                  </span>
                  Real-Time Parsing Active
                </div>
                <span className="font-semibold text-slate-300">
                  {progressPercent}% Complete ({pagesProcessed} / {totalPages > 0 ? totalPages : '...'} Pages)
                </span>
              </div>

              {/* Animated Progress Bar */}
              <div className="w-full bg-slate-800 rounded-full h-4 overflow-hidden border border-slate-700 relative shadow-inner">
                <div
                  className="bg-gradient-to-r from-blue-500 via-indigo-500 to-emerald-400 h-full transition-all duration-300 ease-out flex items-center justify-end pr-2 text-[10px] font-bold text-white shadow-sm"
                  style={{ width: `${Math.max(progressPercent, 4)}%` }}
                >
                  {progressPercent >= 10 && `${progressPercent}%`}
                </div>
              </div>

              {/* Status Message */}
              <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
                <div className="flex items-center gap-2">
                  <RefreshCw className="w-3.5 h-3.5 text-primary-400 animate-spin flex-shrink-0" />
                  <span className="truncate">
                    {progressPercent < 10
                      ? 'Initializing PDF grid layout parser...'
                      : progressPercent < 95
                      ? `Scraping & extracting cutoffs from page ${pagesProcessed} of ${totalPages}...`
                      : 'Finalizing database commits & institute metadata...'}
                  </span>
                </div>
                <span className="font-mono text-emerald-400 text-xs font-semibold whitespace-nowrap ml-2">
                  {recordsCreated.toLocaleString()} records extracted
                </span>
              </div>

              {/* Mini Stats Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2">
                <div className="bg-slate-800/80 p-3 rounded-lg border border-slate-700/60">
                  <span className="text-[11px] text-slate-400 block">Pages Processed</span>
                  <span className="text-base font-bold text-slate-100">
                    {pagesProcessed} / {totalPages > 0 ? totalPages : '...'}
                  </span>
                </div>
                <div className="bg-slate-800/80 p-3 rounded-lg border border-slate-700/60">
                  <span className="text-[11px] text-slate-400 block">Cutoff Records</span>
                  <span className="text-base font-bold text-emerald-400">
                    {recordsCreated.toLocaleString()}
                  </span>
                </div>
                <div className="bg-slate-800/80 p-3 rounded-lg border border-slate-700/60 col-span-2 sm:col-span-1">
                  <span className="text-[11px] text-slate-400 block">Status</span>
                  <span className="text-xs font-semibold text-sky-400 uppercase tracking-wide">
                    PROCESSING
                  </span>
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-center gap-3 pt-2">
            {!isProcessing && (
              <Button
                variant="outline"
                onClick={() => setBatchId(null)}
              >
                Cancel / Choose Another File
              </Button>
            )}
            <Button
              onClick={() => processMutation.mutate()}
              isLoading={isProcessing}
              size="lg"
              className="bg-primary-600 hover:bg-primary-700 text-white font-semibold px-8"
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
