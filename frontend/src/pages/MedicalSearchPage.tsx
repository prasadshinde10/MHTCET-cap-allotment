import React, { useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Building2, BookOpen, Download, LayoutGrid, Table as TableIcon,
  Filter, Sparkles, RefreshCw, Stethoscope, Activity, Calendar,
  Layers, HelpCircle, Database, UploadCloud, Trash2, CheckCircle2,
  AlertTriangle, FileText, ArrowRight, Check, Globe, MapPin, Award
} from 'lucide-react';
import toast from 'react-hot-toast';

import { 
  getMedicalFilterOptions, 
  getMedicalCutoffs, 
  getMedicalStats,
  getMedicalExportUrl,
  resetMedicalDatabase,
  restoreMedicalDatabase,
  uploadMedicalPdf,
  MedicalCutoffItem,
  MedicalUploadResult,
} from '../api/medical';
import SearchableSelect, { SearchableOption } from '../components/ui/SearchableSelect';
import { FileDropzone } from '../components/ui/FileDropzone';
import Button from '../components/ui/Button';
import FilterChips, { ActiveFilter } from '../components/ui/FilterChips';
import Spinner from '../components/ui/Spinner';
import { Pagination } from '../components/ui/Pagination';
import { formatNumber } from '../utils/formatters';

export const MedicalSearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

  const [viewMode, setViewMode] = useState<'table' | 'cards' | 'comparison'>('table');
  const [selectedForCompare, setSelectedForCompare] = useState<MedicalCutoffItem[]>([]);

  // Medical Data Management & Ingestion states
  const [showAdminPanel, setShowAdminPanel] = useState<boolean>(false);
  const [showResetConfirm, setShowResetConfirm] = useState<boolean>(false);
  const [showRestoreConfirm, setShowRestoreConfirm] = useState<boolean>(false);

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadYear, setUploadYear] = useState<string>('auto');
  const [uploadRound, setUploadRound] = useState<string>('auto');
  const [uploadStream, setUploadStream] = useState<string>('auto');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadResult, setUploadResult] = useState<MedicalUploadResult | null>(null);

  // Mutations for isolated medical.db operations
  const resetMutation = useMutation({
    mutationFn: resetMedicalDatabase,
    onSuccess: (data) => {
      toast.success(data.message || 'Medical database wiped successfully!');
      setShowResetConfirm(false);
      setUploadResult(null);
      queryClient.invalidateQueries({ queryKey: ['medicalCutoffs'] });
      queryClient.invalidateQueries({ queryKey: ['medicalFilterOptions'] });
      queryClient.invalidateQueries({ queryKey: ['medicalStats'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.message || 'Failed to wipe medical database');
    }
  });

  const restoreMutation = useMutation({
    mutationFn: restoreMedicalDatabase,
    onSuccess: (data) => {
      toast.success(data.message || 'Medical dataset restored successfully!');
      setShowRestoreConfirm(false);
      setUploadResult(null);
      queryClient.invalidateQueries({ queryKey: ['medicalCutoffs'] });
      queryClient.invalidateQueries({ queryKey: ['medicalFilterOptions'] });
      queryClient.invalidateQueries({ queryKey: ['medicalStats'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.message || 'Failed to restore medical dataset');
    }
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!uploadFile) throw new Error('Please select a PDF file first');
      return uploadMedicalPdf(
        uploadFile,
        uploadYear === 'auto' ? undefined : uploadYear,
        uploadRound === 'auto' ? undefined : uploadRound,
        uploadStream === 'auto' ? undefined : uploadStream
      );
    },
    onMutate: () => {
      setIsUploading(true);
    },
    onSuccess: (data) => {
      toast.success(`PDF parsed successfully! Created ${data.records_created.toLocaleString()} medical cutoffs.`);
      setIsUploading(false);
      setUploadResult(data);
      queryClient.invalidateQueries({ queryKey: ['medicalCutoffs'] });
      queryClient.invalidateQueries({ queryKey: ['medicalFilterOptions'] });
      queryClient.invalidateQueries({ queryKey: ['medicalStats'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.message || 'Medical PDF parsing failed');
      setIsUploading(false);
    }
  });

  // Counselling Stream state: 'central' (MCC) vs 'state' (Maharashtra CET Cell)
  const counsellingParam = (searchParams.get('counselling') as 'central' | 'state') || 'central';

  // URL state query parameters
  const defaultYear = counsellingParam === 'central' ? '2026-2027' : '2024-2025';
  const yearParam = searchParams.get('year') || defaultYear;
  const roundParam = searchParams.get('round') || '';
  const collegeParam = searchParams.get('college') || '';
  const courseParam = searchParams.get('course') || '';
  const collegeTypeParam = searchParams.get('type') || '';
  const stateParam = searchParams.get('state') || '';
  const cityParam = searchParams.get('city') || '';
  const categoryParam = searchParams.get('category') || '';
  const quotaParam = searchParams.get('quota') || '';
  const genderParam = searchParams.get('gender') || '';
  const rankParam = searchParams.get('student_rank') || '';
  const scoreParam = searchParams.get('student_score') || '';
  const sortParam = searchParams.get('sort_by') || 'rank_asc';
  const pageParam = parseInt(searchParams.get('page') || '1', 10);
  const pageSizeParam = parseInt(searchParams.get('page_size') || '50', 10);

  // Multi-select parsed arrays
  const selectedColleges = useMemo(
    () => (collegeParam ? collegeParam.split('||').map((c) => c.trim()).filter(Boolean) : []),
    [collegeParam]
  );
  const selectedCourses = useMemo(
    () => (courseParam ? courseParam.split('||').map((p) => p.trim()).filter(Boolean) : []),
    [courseParam]
  );

  // Dynamic filter options query based on selected counselling stream (Central vs State)
  const { data: filterOptions, isLoading: isOptionsLoading } = useQuery({
    queryKey: ['medicalFilterOptions', counsellingParam],
    queryFn: () => getMedicalFilterOptions(counsellingParam),
  });

  // Database stats query
  const { data: dbStats, isLoading: isStatsLoading } = useQuery({
    queryKey: ['medicalStats'],
    queryFn: getMedicalStats,
  });

  // Query cutoffs
  const queryArgs = useMemo(() => {
    return {
      counselling_type: counsellingParam,
      academic_year: yearParam === 'ALL' ? undefined : yearParam,
      round_name: roundParam || undefined,
      college_name: collegeParam || undefined,
      course_name: courseParam || undefined,
      college_type: collegeTypeParam || undefined,
      state: stateParam || undefined,
      city: cityParam || undefined,
      category: categoryParam || undefined,
      quota: quotaParam || undefined,
      gender: genderParam || undefined,
      student_rank: rankParam ? parseInt(rankParam, 10) : undefined,
      page: pageParam,
      page_size: pageSizeParam,
      sort_by: sortParam,
    };
  }, [
    counsellingParam, yearParam, roundParam, collegeParam, courseParam, collegeTypeParam,
    stateParam, cityParam, categoryParam, quotaParam, genderParam, rankParam,
    pageParam, pageSizeParam, sortParam
  ]);

  const { data: cutoffsData, isLoading: isCutoffsLoading, isFetching: isCutoffsFetching } = useQuery({
    queryKey: ['medicalCutoffs', queryArgs],
    queryFn: () => getMedicalCutoffs(queryArgs),
    placeholderData: (prev) => prev,
  });

  // Update query params helper
  const updateQueryParam = (key: string, value: string | null) => {
    const nextParams = new URLSearchParams(searchParams);
    if (value === null || value === '' || value === undefined) {
      nextParams.delete(key);
    } else {
      nextParams.set(key, value);
    }
    // Always reset to page 1 on filter changes unless modifying page itself
    if (key !== 'page') {
      nextParams.set('page', '1');
    }
    setSearchParams(nextParams);
  };

  const handleSwitchCounselling = (mode: 'central' | 'state') => {
    const nextParams = new URLSearchParams();
    nextParams.set('counselling', mode);
    nextParams.set('year', mode === 'central' ? '2026-2027' : '2024-2025');
    nextParams.set('sort_by', 'rank_asc');
    nextParams.set('page', '1');
    nextParams.set('page_size', '50');
    setSearchParams(nextParams);
    toast.success(
      mode === 'central'
        ? 'Switched to All India Central Counselling (MCC - AIQ)'
        : 'Switched to Maharashtra State Medical Counselling (CET Cell)'
    );
  };

  const clearAllFilters = () => {
    const nextParams = new URLSearchParams();
    nextParams.set('counselling', counsellingParam);
    nextParams.set('year', counsellingParam === 'central' ? '2026-2027' : '2024-2025');
    nextParams.set('sort_by', 'rank_asc');
    nextParams.set('page', '1');
    nextParams.set('page_size', '50');
    setSearchParams(nextParams);
    toast.success('All filters reset');
  };

  // Convert colleges to SearchableOption format
  const collegeOptions: SearchableOption[] = useMemo(() => {
    if (!filterOptions?.colleges) return [];
    return filterOptions.colleges.map((c) => ({
      value: c.college_name,
      label: `${c.college_code} - ${c.college_name}`,
      sublabel: `${c.college_type || 'College'} • ${c.city ? `${c.city}, ` : ''}${c.state || 'India'}`,
    }));
  }, [filterOptions]);

  // Convert courses to SearchableOption format
  const courseOptions: SearchableOption[] = useMemo(() => {
    if (!filterOptions?.courses) return [];
    return filterOptions.courses.map((cr) => ({
      value: cr.course_code,
      label: `${cr.course_code} - ${cr.course_name}`,
      sublabel: cr.degree_type,
    }));
  }, [filterOptions]);

  // Quick categories
  const categoriesList = useMemo(() => {
    return filterOptions?.categories || ['OPEN', 'OBC', 'EWS', 'SC', 'ST', 'VJ / NT-A', 'NT1 (NT-B)', 'NT2 (NT-C)', 'NT3 (NT-D)', 'SEBC', 'Defense', 'PwD / PH', 'NRI / IQ'];
  }, [filterOptions]);

  // Active filters list for chips
  const activeFilters: ActiveFilter[] = useMemo(() => {
    const filters: ActiveFilter[] = [];
    if (yearParam && yearParam !== 'ALL') {
      filters.push({
        id: 'year',
        label: 'Year',
        value: yearParam,
      });
    }
    if (roundParam) {
      filters.push({
        id: 'round',
        label: 'Round',
        value: roundParam,
      });
    }
    if (selectedCourses.length > 0) {
      selectedCourses.forEach((c) => {
        filters.push({
          id: `course_${c}`,
          label: 'Course',
          value: c,
        });
      });
    }
    if (selectedColleges.length > 0) {
      selectedColleges.forEach((c) => {
        filters.push({
          id: `college_${c}`,
          label: 'College',
          value: c.length > 25 ? `${c.substring(0, 25)}...` : c,
        });
      });
    }
    if (collegeTypeParam) {
      filters.push({
        id: 'college_type',
        label: 'Type',
        value: collegeTypeParam,
      });
    }
    if (stateParam) {
      filters.push({
        id: 'state',
        label: 'State',
        value: stateParam,
      });
    }
    if (cityParam) {
      filters.push({
        id: 'city',
        label: 'City',
        value: cityParam,
      });
    }
    if (categoryParam) {
      filters.push({
        id: 'category',
        label: 'Category',
        value: categoryParam,
      });
    }
    if (quotaParam) {
      filters.push({
        id: 'quota',
        label: 'Quota',
        value: quotaParam.length > 25 ? `${quotaParam.substring(0, 25)}...` : quotaParam,
      });
    }
    if (genderParam) {
      filters.push({
        id: 'gender',
        label: 'Seat Quota / Gender',
        value: genderParam === 'women' ? 'Women Quota (30%)' : 'General Seats (Open to All)',
      });
    }
    if (rankParam) {
      filters.push({
        id: 'rank',
        label: 'NEET AIR ≤',
        value: formatNumber(parseInt(rankParam, 10)),
      });
    }
    return filters;
  }, [
    yearParam, roundParam, stateParam, cityParam, selectedCourses, selectedColleges,
    collegeTypeParam, categoryParam, quotaParam, genderParam, rankParam
  ]);

  const handleRemoveFilter = (filterId: string) => {
    if (filterId === 'year') updateQueryParam('year', 'ALL');
    else if (filterId === 'round') updateQueryParam('round', null);
    else if (filterId === 'state') updateQueryParam('state', null);
    else if (filterId === 'city') updateQueryParam('city', null);
    else if (filterId === 'college_type') updateQueryParam('type', null);
    else if (filterId === 'category') updateQueryParam('category', null);
    else if (filterId === 'quota') updateQueryParam('quota', null);
    else if (filterId === 'gender') updateQueryParam('gender', null);
    else if (filterId === 'rank') updateQueryParam('student_rank', null);
    else if (filterId === 'score') updateQueryParam('student_score', null);
    else if (filterId.startsWith('course_')) {
      const removed = filterId.replace('course_', '');
      const remaining = selectedCourses.filter((c) => c !== removed);
      updateQueryParam('course', remaining.length > 0 ? remaining.join('||') : null);
    } else if (filterId.startsWith('college_')) {
      const removed = filterId.replace('college_', '');
      const remaining = selectedColleges.filter((c) => c !== removed);
      updateQueryParam('college', remaining.length > 0 ? remaining.join('||') : null);
    }
  };

  const handleExportCsv = () => {
    const exportUrl = getMedicalExportUrl(queryArgs);
    window.open(exportUrl, '_blank');
    toast.success('Downloading NEET Medical cutoffs CSV...');
  };

  const toggleCompare = (item: MedicalCutoffItem) => {
    const exists = selectedForCompare.some((x) => x.id === item.id);
    if (exists) {
      setSelectedForCompare(selectedForCompare.filter((x) => x.id !== item.id));
      toast('Removed from comparison');
    } else {
      if (selectedForCompare.length >= 4) {
        toast.error('You can compare a maximum of 4 colleges at a time');
        return;
      }
      setSelectedForCompare([...selectedForCompare, item]);
      toast.success('Added to comparison');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Page Header Banner: Crisp Medical Emerald Gradient */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-emerald-700 via-teal-700 to-emerald-800 border border-emerald-600/30 p-6 lg:p-8 shadow-md text-white">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 border border-white/20 text-emerald-100 text-xs font-semibold tracking-wide uppercase backdrop-blur-xs">
              <Stethoscope className="w-3.5 h-3.5" />
              {counsellingParam === 'central'
                ? 'MCC All India Quota (AIQ) • Central & Deemed Counselling'
                : 'State Common Entrance Test Cell • Maharashtra NEET (UG) Counselling'}
            </div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-white flex items-center gap-3">
              {counsellingParam === 'central'
                ? 'MCC Central Medical Allotment Cutoffs'
                : 'Maharashtra Medical & AYUSH Cutoffs'}
            </h1>
            <p className="text-emerald-100 text-sm max-w-3xl leading-relaxed">
              {counsellingParam === 'central'
                ? 'Explore official Medical Counselling Committee (MCC) NEET-UG cutoffs across AIIMS, JIPMER, Central Universities, Deemed Universities, and 15% All India Quota nationwide.'
                : 'Explore official State CET Cell NEET-UG allotment cutoffs across Government & Private Medical, Dental, Ayurvedic, Homeopathic, Physiotherapy & Nursing Colleges in Maharashtra.'}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              size="sm"
              onClick={() => setShowAdminPanel(!showAdminPanel)}
              className={`font-semibold shadow-xs transition-all ${
                showAdminPanel 
                  ? 'bg-white text-emerald-900 border border-white hover:bg-emerald-50' 
                  : 'bg-white/15 hover:bg-white/25 text-white border border-white/30 backdrop-blur-xs'
              }`}
            >
              <Database className="w-4 h-4 mr-2 text-emerald-200" />
              {showAdminPanel ? 'Close Ingestion Panel' : 'Manage Data & Upload PDF'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportCsv}
              className="bg-white/10 hover:bg-white/20 text-white border-white/30 backdrop-blur-xs shadow-xs"
            >
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                queryClient.invalidateQueries({ queryKey: ['medicalCutoffs'] });
                queryClient.invalidateQueries({ queryKey: ['medicalStats'] });
                queryClient.invalidateQueries({ queryKey: ['medicalFilterOptions'] });
                toast.success('Medical data refreshed');
              }}
              className="bg-white text-emerald-800 hover:bg-emerald-50 hover:text-emerald-900 border border-transparent shadow-xs font-semibold"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>

        {/* Database Stats Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-white/15">
          <div className="bg-white/10 backdrop-blur rounded-xl p-3.5 border border-white/15">
            <div className="text-xs font-medium text-emerald-100 flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5" />
              Total Colleges
            </div>
            <div className="text-xl font-bold text-white mt-1">
              {isStatsLoading ? '...' : formatNumber(dbStats?.college_count || 0)}
            </div>
            <div className="text-[11px] text-emerald-200 mt-0.5">
              Nationwide & Maharashtra
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur rounded-xl p-3.5 border border-white/15">
            <div className="text-xs font-medium text-emerald-100 flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5" />
              MCC Central (AIQ)
            </div>
            <div className="text-xl font-bold text-white mt-1">
              {isStatsLoading ? '...' : formatNumber(dbStats?.mcc_cutoff_count || 18335)}
            </div>
            <div className="text-[11px] text-emerald-200 mt-0.5">
              Cutoffs Across 35 States
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur rounded-xl p-3.5 border border-white/15">
            <div className="text-xs font-medium text-emerald-100 flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5" />
              State CET Cell
            </div>
            <div className="text-xl font-bold text-white mt-1">
              {isStatsLoading ? '...' : formatNumber(dbStats?.state_cutoff_count || 15278)}
            </div>
            <div className="text-[11px] text-emerald-200 mt-0.5">
              Maharashtra 85% Cutoffs
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur rounded-xl p-3.5 border border-white/15">
            <div className="text-xs font-medium text-emerald-100 flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5" />
              Courses & Years
            </div>
            <div className="text-xl font-bold text-white mt-1">
              {isStatsLoading ? '...' : `${dbStats?.course_count || 8} Courses`}
            </div>
            <div className="text-[11px] text-emerald-200 mt-0.5">
              MBBS, BDS, AYUSH, PT & Nursing
            </div>
          </div>
        </div>
      </div>

      {/* Empty Database Alert Banner (if medical.db cutoffs are 0) */}
      {dbStats && dbStats.cutoff_count === 0 && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 text-slate-800 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-in fade-in">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
            <div>
              <p className="font-bold text-amber-900 text-sm">Medical database is currently empty (0 records).</p>
              <p className="text-xs text-amber-800 mt-0.5">
                Upload and parse new Medical Cutoff PDFs below, or restore the official verified dataset (33,613 records) anytime.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button
              size="sm"
              onClick={() => setShowRestoreConfirm(true)}
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold"
            >
              <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
              Restore 33,613 Records
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowAdminPanel(true)}
              className="text-xs border-amber-300 text-amber-900 hover:bg-amber-100"
            >
              <UploadCloud className="w-3.5 h-3.5 mr-1.5" />
              Upload PDF
            </Button>
          </div>
        </div>
      )}

      {/* Dedicated Medical Section Data Management & PDF Ingestion Panel */}
      {(showAdminPanel || (dbStats && dbStats.cutoff_count === 0)) && (
        <div className="bg-white border-2 border-emerald-500/30 rounded-2xl p-6 shadow-md space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-3">
            <div>
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-700">
                <Database className="w-4 h-4" />
                Dedicated Medical Section Data Controls
              </div>
              <h3 className="text-lg font-extrabold text-slate-900 mt-0.5">
                Medical PDF Ingestion & Database Management
              </h3>
              <p className="text-xs text-slate-500">
                Upload and parse official Medical Cutoff PDFs directly into dedicated <span className="font-mono text-emerald-800">medical_central.db</span> (MCC) or <span className="font-mono text-teal-800">medical_state.db</span> (State CET Cell). All other sections (CET, JoSAA, IISER, BITS) remain completely untouched.
              </p>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <Button
                size="sm"
                onClick={() => setShowRestoreConfirm(true)}
                disabled={restoreMutation.isPending}
                className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs"
                title="Restore official pre-verified medical dataset"
              >
                <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                Restore Verified Datasets (33,613)
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => setShowResetConfirm(true)}
                disabled={resetMutation.isPending}
                className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold shadow-xs"
              >
                <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                Clear / Delete Medical Data
              </Button>
            </div>
          </div>

          {/* Database Status Grid (Separated Central and State DBs) */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div>
              <span className="text-xs text-slate-500 block">Central MCC Database</span>
              <span className="text-lg font-bold text-emerald-700">
                {isStatsLoading ? '...' : formatNumber(dbStats?.mcc_cutoff_count || 0)}
              </span>
              <span className="text-[10px] text-slate-400 block font-mono">medical_central.db</span>
            </div>
            <div>
              <span className="text-xs text-slate-500 block">State CET Cell Database</span>
              <span className="text-lg font-bold text-teal-700">
                {isStatsLoading ? '...' : formatNumber(dbStats?.state_cutoff_count || 0)}
              </span>
              <span className="text-[10px] text-slate-400 block font-mono">medical_state.db</span>
            </div>
            <div>
              <span className="text-xs text-slate-500 block">Total Colleges</span>
              <span className="text-lg font-bold text-slate-800">
                {isStatsLoading ? '...' : formatNumber(dbStats?.college_count || 0)}
              </span>
              <span className="text-[10px] text-slate-400 block">791 Central • 439 State</span>
            </div>
            <div>
              <span className="text-xs text-slate-500 block">Database Storage</span>
              <span className="text-xs font-mono font-bold text-emerald-800 bg-white px-2 py-1 rounded border border-emerald-200 inline-block mt-0.5">
                Separated Databases
              </span>
              <span className="text-[10px] text-slate-400 block mt-0.5">CET / JoSAA untouched</span>
            </div>
          </div>

          {/* Ingestion Result Summary Card */}
          {uploadResult && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 space-y-3">
              <div className="flex items-center gap-2 text-emerald-800 font-bold text-sm">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                Medical PDF Parsed & Ingested Successfully!
              </div>
              <p className="text-xs text-emerald-900">{uploadResult.message}</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-1">
                <div className="bg-white p-2.5 rounded-lg border border-emerald-100">
                  <span className="text-slate-500 block text-[11px]">Records Created</span>
                  <span className="font-bold text-emerald-700 text-sm">{uploadResult.records_created.toLocaleString()}</span>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-emerald-100">
                  <span className="text-slate-500 block text-[11px]">Total in medical.db</span>
                  <span className="font-bold text-slate-800 text-sm">{uploadResult.total_cutoffs.toLocaleString()}</span>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-emerald-100">
                  <span className="text-slate-500 block text-[11px]">Colleges in DB</span>
                  <span className="font-bold text-slate-800 text-sm">{uploadResult.total_colleges.toLocaleString()}</span>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-emerald-100">
                  <span className="text-slate-500 block text-[11px]">Processing Time</span>
                  <span className="font-mono text-slate-800 text-sm">{uploadResult.duration_seconds}s</span>
                </div>
              </div>
              <div className="flex gap-2 pt-1">
                <Button
                  size="sm"
                  onClick={() => {
                    setUploadResult(null);
                    setUploadFile(null);
                  }}
                  variant="outline"
                  className="text-xs bg-white text-slate-700"
                >
                  Upload Another PDF
                </Button>
                <Button
                  size="sm"
                  onClick={() => {
                    setShowAdminPanel(false);
                    toast.success('Showing updated cutoffs table');
                  }}
                  className="text-xs bg-emerald-700 hover:bg-emerald-800 text-white font-semibold"
                >
                  Inspect in Table Below
                  <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                </Button>
              </div>
            </div>
          )}

          {/* PDF Upload Dropzone & Configuration Form */}
          {!uploadResult && (
            <div className="space-y-4 pt-1">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Counselling Stream / Format
                  </label>
                  <select
                    value={uploadStream}
                    onChange={(e) => setUploadStream(e.target.value)}
                    className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs"
                  >
                    <option value="auto">Auto-Detect from PDF Content (Recommended)</option>
                    <option value="MCC_AIQ">MCC NEET-UG All India Quota (AIQ)</option>
                    <option value="MAHA_SELECTION">Maharashtra State Selection List</option>
                    <option value="MAHA_SUMMARY">Maharashtra State Summary Matrix</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Target Academic Year
                  </label>
                  <select
                    value={uploadYear}
                    onChange={(e) => setUploadYear(e.target.value)}
                    className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs"
                  >
                    <option value="auto">Auto-Detect from PDF</option>
                    <option value="2026-2027">2026-2027</option>
                    <option value="2025-2026">2025-2026</option>
                    <option value="2024-2025">2024-2025</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Counselling Round
                  </label>
                  <select
                    value={uploadRound}
                    onChange={(e) => setUploadRound(e.target.value)}
                    className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs"
                  >
                    <option value="auto">Auto-Detect from PDF</option>
                    <option value="Round 1">Round 1</option>
                    <option value="Round 2">Round 2</option>
                    <option value="Round 3">Round 3</option>
                    <option value="Round 4">Round 4</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Select Medical Cutoff PDF File
                </label>
                <FileDropzone
                  onFileSelect={(f) => setUploadFile(f)}
                  accept=".pdf"
                  maxSizeMB={150}
                />
              </div>

              <div className="flex items-center justify-between pt-2">
                <div className="text-xs text-slate-500 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Files are parsed into <span className="font-mono text-emerald-800">medical.db</span> and immediately available in search.</span>
                </div>

                <Button
                  size="md"
                  onClick={() => uploadMutation.mutate()}
                  disabled={!uploadFile || isUploading}
                  isLoading={isUploading}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-6 shadow-xs"
                >
                  <UploadCloud className="w-4 h-4 mr-2" />
                  {isUploading ? 'Parsing PDF & Ingesting...' : 'Upload & Parse PDF'}
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Confirmation Modal for Wiping Medical Database */}
      {showResetConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 space-y-4 border border-rose-200 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3 text-rose-600">
              <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5 text-rose-600" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-base">Delete All Medical Data (100% Wipe)?</h3>
                <p className="text-xs text-rose-600 font-medium">This will completely clear the medical database.</p>
              </div>
            </div>
            <div className="text-xs text-slate-600 bg-amber-50 border border-amber-200 rounded-xl p-3.5 space-y-2">
              <p className="font-semibold text-amber-900">Safety & Isolation Details:</p>
              <p>1. Only the dedicated <span className="font-mono font-semibold text-slate-800">medical.db</span> will be cleared.</p>
              <p>2. MHT-CET (<span className="font-mono">cutoff.db</span>), JoSAA (<span className="font-mono">josaa.db</span>), IISER, and BITS databases remain <strong>100% untouched</strong>.</p>
              <p>3. After wiping, you can upload new PDF files or click <strong>"Restore Verified Dataset"</strong> anytime.</p>
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
                className="bg-rose-600 hover:bg-rose-700 text-white font-semibold"
              >
                Yes, Wipe Medical Data
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal for Restoring Official Dataset */}
      {showRestoreConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 space-y-4 border border-emerald-200 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3 text-emerald-600">
              <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-base">Restore Verified Medical Cutoffs?</h3>
                <p className="text-xs text-emerald-700 font-medium">Restores 33,613 official cutoffs across 1,230 colleges.</p>
              </div>
            </div>
            <div className="text-xs text-slate-600 bg-emerald-50/70 border border-emerald-200 rounded-xl p-3.5 space-y-1.5">
              <p className="font-semibold text-emerald-950">Verified Dataset Summary:</p>
              <p>• <strong>MCC All India Quota:</strong> 26,287 records across 2025 & 2026 (Rounds 1–3).</p>
              <p>• <strong>Maharashtra State Quota:</strong> 7,326 records across MBBS, BDS, BAMS, BHMS, BPTH, BOTH, BUMS.</p>
              <p>• <strong>Colleges:</strong> 1,230 colleges nationwide (AIIMS, Central, Govt, Deemed).</p>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowRestoreConfirm(false)}
                disabled={restoreMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => restoreMutation.mutate()}
                isLoading={restoreMutation.isPending}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
              >
                Yes, Restore 33,613 Records
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Top Counselling Stream Selector Tabs (Central MCC vs State CET Cell) */}
      <div className="bg-white border border-slate-200 rounded-2xl p-2 shadow-xs">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {/* Central Counselling (MCC) Tab */}
          <button
            type="button"
            onClick={() => handleSwitchCounselling('central')}
            className={`flex items-start gap-3.5 p-3.5 rounded-xl border text-left transition-all ${
              counsellingParam === 'central'
                ? 'bg-emerald-50/70 border-emerald-500 shadow-xs ring-1 ring-emerald-500'
                : 'bg-white border-transparent hover:bg-slate-50 text-slate-600'
            }`}
          >
            <div className={`p-2.5 rounded-xl shrink-0 ${
              counsellingParam === 'central'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'bg-slate-100 text-slate-500'
            }`}>
              <Globe className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-sm font-bold ${
                  counsellingParam === 'central' ? 'text-emerald-950' : 'text-slate-800'
                }`}>
                  Central Counselling (MCC)
                </span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                  AIQ • AIIMS • Central
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1 line-clamp-1">
                All India Quota (15%), AIIMS, JIPMER, Deemed Universities & Central Institutes across 35 States
              </p>
              <div className="flex items-center gap-2 mt-2 text-[11px] font-medium text-emerald-700">
                <span>{dbStats?.mcc_cutoff_count ? formatNumber(dbStats.mcc_cutoff_count) : '18,335'} Cutoffs</span>
                <span>•</span>
                <span>791 Colleges</span>
                <span>•</span>
                <span>MBBS, BDS, B.Sc. Nursing</span>
              </div>
            </div>
          </button>

          {/* State Counselling (Maharashtra CET Cell) Tab */}
          <button
            type="button"
            onClick={() => handleSwitchCounselling('state')}
            className={`flex items-start gap-3.5 p-3.5 rounded-xl border text-left transition-all ${
              counsellingParam === 'state'
                ? 'bg-teal-50/70 border-teal-500 shadow-xs ring-1 ring-teal-500'
                : 'bg-white border-transparent hover:bg-slate-50 text-slate-600'
            }`}
          >
            <div className={`p-2.5 rounded-xl shrink-0 ${
              counsellingParam === 'state'
                ? 'bg-teal-600 text-white shadow-xs'
                : 'bg-slate-100 text-slate-500'
            }`}>
              <MapPin className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-sm font-bold ${
                  counsellingParam === 'state' ? 'text-teal-950' : 'text-slate-800'
                }`}>
                  State Medical Counselling (CET Cell)
                </span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-teal-100 text-teal-800 border border-teal-200">
                  Maharashtra 85% State Quota
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1 line-clamp-1">
                Maharashtra Government & Private Medical, Dental, Ayurvedic, Homeopathic & Allied Health Colleges
              </p>
              <div className="flex items-center gap-2 mt-2 text-[11px] font-medium text-teal-700">
                <span>{dbStats?.state_cutoff_count ? formatNumber(dbStats.state_cutoff_count) : '15,278'} Cutoffs</span>
                <span>•</span>
                <span>439 Colleges</span>
                <span>•</span>
                <span>MBBS, BDS, BAMS, BHMS, BPTH...</span>
              </div>
            </div>
          </button>
        </div>
      </div>

      {/* Stream-Specific NEET Rank Eligibility Predictor (Rank-Only for 100% Accuracy) */}
      {counsellingParam === 'central' ? (
        <div className="bg-gradient-to-r from-emerald-50 via-teal-50/60 to-white border border-emerald-200 rounded-xl p-5 shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-emerald-900 font-semibold text-sm">
                <Sparkles className="w-4 h-4 text-emerald-600" />
                <span>MCC All India Quota (AIQ) & Central Rank Predictor</span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                  100% Accuracy (AIR Only)
                </span>
              </div>
              <p className="text-xs text-slate-600">
                MCC central allotments are governed strictly by NEET All India Rank (AIR). Enter your AIR to accurately evaluate closing rank cutoffs across AIIMS, Central, Deemed, and AIQ seats.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 shrink-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-700 whitespace-nowrap">Your NEET AIR:</span>
                <input
                  type="number"
                  placeholder="e.g. 15400"
                  value={rankParam}
                  onChange={(e) => updateQueryParam('student_rank', e.target.value ? e.target.value : null)}
                  className="w-40 bg-white border border-emerald-300 rounded-lg px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs placeholder-slate-400 font-medium"
                />
              </div>

              {rankParam && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => updateQueryParam('student_rank', null)}
                  className="text-xs text-slate-500 hover:text-slate-800"
                >
                  Clear Rank
                </Button>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-gradient-to-r from-teal-50 via-emerald-50/60 to-white border border-teal-200 rounded-xl p-5 shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-teal-900 font-semibold text-sm">
                <Sparkles className="w-4 h-4 text-teal-600" />
                <span>Maharashtra State Medical (CET Cell) Rank Predictor</span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-teal-100 text-teal-800 border border-teal-200">
                  100% Accuracy (AIR Only)
                </span>
              </div>
              <p className="text-xs text-slate-600">
                State CET Cell seat allocation operates strictly on your NEET All India Rank (AIR). Enter your AIR to evaluate admission chances in Maharashtra Govt & Private medical colleges.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 shrink-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-700 whitespace-nowrap">Your NEET AIR:</span>
                <input
                  type="number"
                  placeholder="e.g. 24500"
                  value={rankParam}
                  onChange={(e) => updateQueryParam('student_rank', e.target.value ? e.target.value : null)}
                  className="w-40 bg-white border border-teal-300 rounded-lg px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-500 shadow-xs placeholder-slate-400 font-medium"
                />
              </div>

              {rankParam && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => updateQueryParam('student_rank', null)}
                  className="text-xs text-slate-500 hover:text-slate-800"
                >
                  Clear Rank
                </Button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Stream-Specific Filter Section (Light Theme) */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4 shadow-xs">
        <div className="flex items-center justify-between pb-2 border-b border-slate-100">
          <div className="flex items-center gap-2 text-slate-800 font-semibold text-sm">
            <Filter className="w-4 h-4 text-emerald-600" />
            {counsellingParam === 'central'
              ? 'Central Counselling Filters (MCC All India Quota)'
              : 'Maharashtra State Counselling Filters (CET Cell)'}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllFilters}
              className="text-xs text-slate-500 hover:text-emerald-700"
            >
              Reset Filters
            </Button>
          </div>
        </div>

        {/* Filter Inputs Grid tailored for Central (MCC) vs State (CET Cell) */}
        {counsellingParam === 'central' ? (
          /* Central Counselling Filters */
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Academic Year */}
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Academic Year</label>
                <select
                  value={yearParam}
                  onChange={(e) => updateQueryParam('year', e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs"
                >
                  <option value="ALL">All Available Years</option>
                  {filterOptions?.academic_years.map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
              </div>

              {/* MCC Round */}
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">MCC Counselling Round</label>
                <select
                  value={roundParam}
                  onChange={(e) => updateQueryParam('round', e.target.value || null)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs"
                >
                  <option value="">All MCC Rounds</option>
                  {filterOptions?.rounds.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>

              {/* State / UT Nationwide */}
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  State / Union Territory
                </label>
                <select
                  value={stateParam}
                  onChange={(e) => updateQueryParam('state', e.target.value || null)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs"
                >
                  <option value="">All 35 States / UTs (Nationwide)</option>
                  {filterOptions?.states?.map((st) => (
                    <option key={st} value={st}>{st}</option>
                  ))}
                </select>
              </div>

              {/* College Management / Type */}
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">College Management / Type</label>
                <select
                  value={collegeTypeParam}
                  onChange={(e) => updateQueryParam('type', e.target.value || null)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs"
                >
                  <option value="">All Management Types</option>
                  {filterOptions?.college_types && filterOptions.college_types.length > 0 ? (
                    filterOptions.college_types.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))
                  ) : (
                    <>
                      <option value="AIIMS">AIIMS</option>
                      <option value="Central University">Central University</option>
                      <option value="Deemed / Paid Seats">Deemed / Paid Seats</option>
                      <option value="Government/Aided">Government / Aided</option>
                      <option value="Private">Private</option>
                    </>
                  )}
                </select>
              </div>
            </div>

            {/* Central Quotas & Categories */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Candidate Category</label>
                <select
                  value={categoryParam}
                  onChange={(e) => updateQueryParam('category', e.target.value || null)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs"
                >
                  <option value="">All Categories (OPEN, OBC, EWS, SC, ST, PwD)</option>
                  {categoriesList.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Seat Reservation / Gender
                </label>
                <select
                  value={genderParam}
                  onChange={(e) => updateQueryParam('gender', e.target.value || null)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs"
                >
                  <option value="">All Seats (General & Women Quota)</option>
                  <option value="general">General Seats (Open to All Candidates)</option>
                  <option value="women">Women Quota Seats Only</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  MCC Quota / Seat Type ({filterOptions?.quotas?.length || 0} Quotas)
                </label>
                <select
                  value={quotaParam}
                  onChange={(e) => updateQueryParam('quota', e.target.value || null)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs"
                >
                  <option value="">All Central Quotas (AIQ, Open Seat, Deemed...)</option>
                  {filterOptions?.quotas?.map((q) => (
                    <option key={q} value={q}>{q}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        ) : (
          /* State Counselling Filters */
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Academic Year */}
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Academic Year</label>
                <select
                  value={yearParam}
                  onChange={(e) => updateQueryParam('year', e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-500 shadow-xs"
                >
                  <option value="ALL">All Available Years</option>
                  {filterOptions?.academic_years.map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
              </div>

              {/* CET Cell Round */}
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">State CAP Round</label>
                <select
                  value={roundParam}
                  onChange={(e) => updateQueryParam('round', e.target.value || null)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-500 shadow-xs"
                >
                  <option value="">All State Rounds</option>
                  {filterOptions?.rounds.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>

              {/* Maharashtra District / City */}
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Maharashtra District / City
                </label>
                <select
                  value={cityParam}
                  onChange={(e) => updateQueryParam('city', e.target.value || null)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-500 shadow-xs"
                >
                  <option value="">All Maharashtra Cities ({filterOptions?.cities?.length || 24} Cities)</option>
                  {filterOptions?.cities?.map((ct) => (
                    <option key={ct} value={ct}>{ct}</option>
                  ))}
                </select>
              </div>

              {/* College Management */}
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">College Management</label>
                <select
                  value={collegeTypeParam}
                  onChange={(e) => updateQueryParam('type', e.target.value || null)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-500 shadow-xs"
                >
                  <option value="">All Management Types</option>
                  <option value="Government/Aided">Government / Aided Colleges</option>
                  <option value="Private">Private / Unaided Colleges</option>
                </select>
              </div>
            </div>

            {/* State Reservation Category (Filter A), Gender / Seat Type (Filter B), & Specific Quotas */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Reservation Category (Filter A)
                </label>
                <select
                  value={categoryParam}
                  onChange={(e) => updateQueryParam('category', e.target.value || null)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-500 shadow-xs"
                >
                  <option value="">All Reservation Categories</option>
                  {categoriesList.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Seat Reservation / Gender (Filter B)
                </label>
                <select
                  value={genderParam}
                  onChange={(e) => updateQueryParam('gender', e.target.value || null)}
                  className="w-full bg-white border border-teal-300 rounded-lg px-3 py-2 text-sm text-teal-950 font-medium focus:outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-500 shadow-xs"
                >
                  <option value="">All Seats (General & Women Quota)</option>
                  <option value="general">General Seats (Open to All Candidates)</option>
                  <option value="women">Women Quota Only (30% Horizontal Quota)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Specific Seat Quota (Optional)
                </label>
                <select
                  value={quotaParam}
                  onChange={(e) => updateQueryParam('quota', e.target.value || null)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-teal-600 focus:ring-1 focus:ring-teal-500 shadow-xs"
                >
                  <option value="">All Specific Quotas ({filterOptions?.quotas?.length || 0} Quotas)</option>
                  {filterOptions?.quotas?.map((q) => (
                    <option key={q} value={q}>{q}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Course and College Multi-selects */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
          {/* Courses Searchable Select */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              {counsellingParam === 'central'
                ? 'Central Courses (MBBS, BDS, B.Sc. Nursing)'
                : 'Medical Courses (MBBS, BDS, BAMS, BHMS, BPTH, etc.)'}
            </label>
            <SearchableSelect
              placeholder="All Medical Courses..."
              options={courseOptions}
              multiple={true}
              values={selectedCourses}
              onMultiChange={(vals) => updateQueryParam('course', vals.length > 0 ? vals.join('||') : null)}
            />
          </div>

          {/* Colleges Searchable Select */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              {counsellingParam === 'central'
                ? `MCC Medical Institutes (${collegeOptions.length} Nationwide Colleges)`
                : `Maharashtra Medical Colleges (${collegeOptions.length} State Colleges)`}
            </label>
            <SearchableSelect
              placeholder="All Medical Colleges / AIIMS..."
              options={collegeOptions}
              multiple={true}
              values={selectedColleges}
              onMultiChange={(vals) => updateQueryParam('college', vals.length > 0 ? vals.join('||') : null)}
            />
          </div>
        </div>

        {/* Stream-Specific Quick Course Badges */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-xs text-slate-500 mr-1">Quick Courses:</span>
          {(counsellingParam === 'central'
            ? ['MBBS', 'BDS', 'B.Sc. Nursing']
            : ['MBBS', 'BDS', 'BAMS', 'BHMS', 'BPTH', 'B.Sc. Nursing', 'BOTH', 'BUMS']
          ).map((c) => {
            const isSelected = selectedCourses.includes(c);
            return (
              <button
                key={c}
                type="button"
                onClick={() => {
                  let next;
                  if (isSelected) {
                    next = selectedCourses.filter((x) => x !== c);
                  } else {
                    next = [...selectedCourses, c];
                  }
                  updateQueryParam('course', next.length > 0 ? next.join('||') : null);
                }}
                className={`text-xs px-2.5 py-1 rounded-full font-medium transition-all ${
                  isSelected
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200 hover:text-slate-900 border border-slate-200'
                }`}
              >
                {c}
              </button>
            );
          })}
        </div>

        {/* Active Filter Chips */}
        {activeFilters.length > 0 && (
          <div className="pt-2 border-t border-slate-100">
            <FilterChips
              filters={activeFilters}
              onRemove={handleRemoveFilter}
              onClearAll={clearAllFilters}
            />
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <div className="space-y-4">
        {/* Controls Bar: Results Count, View Toggle, Sorting */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-slate-200 px-4 py-3 rounded-xl shadow-xs">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-slate-900">
              {cutoffsData ? formatNumber(cutoffsData.total) : '0'} Cutoffs Found
            </span>
            {isCutoffsFetching && <Spinner className="w-4 h-4 text-emerald-600" />}
          </div>

          <div className="flex items-center gap-3">
            {/* View Mode Toggle */}
            <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-50">
              <button
                type="button"
                onClick={() => setViewMode('table')}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  viewMode === 'table' ? 'bg-emerald-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <TableIcon className="w-3.5 h-3.5" />
                Table
              </button>
              <button
                type="button"
                onClick={() => setViewMode('cards')}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  viewMode === 'cards' ? 'bg-emerald-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <LayoutGrid className="w-3.5 h-3.5" />
                Cards
              </button>
              {selectedForCompare.length > 0 && (
                <button
                  type="button"
                  onClick={() => setViewMode('comparison')}
                  className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    viewMode === 'comparison' ? 'bg-emerald-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Layers className="w-3.5 h-3.5" />
                  Compare ({selectedForCompare.length})
                </button>
              )}
            </div>

            {/* Sort Dropdown */}
            <select
              value={sortParam}
              onChange={(e) => updateQueryParam('sort_by', e.target.value)}
              className="bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-emerald-600 shadow-xs"
            >
              <option value="rank_asc">Closing AIR (Lowest / Top Ranks)</option>
              <option value="rank_desc">Closing AIR (Highest / Easy Admission)</option>
              <option value="score_desc">Closing NEET Marks (Highest First)</option>
              <option value="score_asc">Closing NEET Marks (Lowest First)</option>
              <option value="year_desc">Academic Year (Recent First)</option>
              <option value="college_asc">College Name (A-Z)</option>
              <option value="course_asc">Course Name (A-Z)</option>
            </select>
          </div>
        </div>

        {/* View Mode: Comparison Panel */}
        {viewMode === 'comparison' && selectedForCompare.length > 0 && (
          <div className="bg-emerald-50/50 border border-emerald-200 rounded-xl p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b border-emerald-200">
              <div className="flex items-center gap-2 text-slate-900 font-bold text-base">
                <Layers className="w-5 h-5 text-emerald-700" />
                Side-by-Side Medical College Comparison
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedForCompare([])}
                  className="text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                >
                  Clear Comparison
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setViewMode('table')}
                  className="text-xs bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                >
                  Back to Table
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {selectedForCompare.map((item) => (
                <div key={item.id} className="bg-white border border-slate-200 rounded-xl p-4 space-y-3 relative shadow-xs">
                  <button
                    onClick={() => toggleCompare(item)}
                    className="absolute top-3 right-3 text-slate-400 hover:text-rose-600 text-xs"
                    title="Remove from comparison"
                  >
                    ✕
                  </button>

                  <div className="space-y-1">
                    <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {item.course_code}
                    </span>
                    <h4 className="text-sm font-bold text-slate-900 line-clamp-2 mt-1">
                      {item.college_name}
                    </h4>
                    <p className="text-xs text-slate-500">
                      Code: {item.college_code} • {item.college_type}
                    </p>
                  </div>

                  <div className="space-y-1.5 pt-2 border-t border-slate-100 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Quota/Category:</span>
                      <span className="font-semibold text-emerald-700">{item.quota_category}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Closing AIR:</span>
                      <span className="font-mono font-bold text-slate-900">
                        {item.closing_rank ? formatNumber(item.closing_rank) : 'N/A'}
                      </span>
                    </div>
                    {item.closing_score && (
                      <div className="flex justify-between">
                        <span className="text-slate-500">NEET Marks:</span>
                        <span className="font-mono font-bold text-teal-700">
                          {item.closing_score} / 720
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span className="text-slate-500">Round:</span>
                      <span className="text-slate-800">{item.round}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Year:</span>
                      <span className="text-slate-800">{item.academic_year}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* View Mode: Table (Light Theme) */}
        {viewMode === 'table' && (
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs sm:text-sm">
                <thead className="bg-slate-50 text-slate-600 text-[11px] uppercase tracking-wider border-b border-slate-200">
                  <tr>
                    <th className="py-3.5 px-4 font-semibold">College & Location</th>
                    <th className="py-3.5 px-3 font-semibold">Course</th>
                    <th className="py-3.5 px-3 font-semibold">Quota / Cat</th>
                    <th className="py-3.5 px-3 font-semibold text-right">Closing AIR</th>
                    <th className="py-3.5 px-3 font-semibold text-right">NEET Marks</th>
                    <th className="py-3.5 px-3 font-semibold text-center">Round</th>
                    <th className="py-3.5 px-3 font-semibold text-center">Year</th>
                    {rankParam && (
                      <th className="py-3.5 px-3 font-semibold text-center">Admission Chance</th>
                    )}
                    <th className="py-3.5 px-3 font-semibold text-center">Compare</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-normal text-slate-700">
                  {isCutoffsLoading ? (
                    <tr>
                      <td colSpan={9} className="py-12 text-center text-slate-500">
                        <div className="flex flex-col items-center justify-center gap-3">
                          <Spinner className="w-6 h-6 text-emerald-600" />
                          <span>Loading Maharashtra medical cutoffs...</span>
                        </div>
                      </td>
                    </tr>
                  ) : !cutoffsData?.items || cutoffsData.items.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-12 text-center text-slate-500">
                        <div className="flex flex-col items-center justify-center gap-2">
                          <HelpCircle className="w-8 h-8 text-slate-400" />
                          <span className="font-semibold text-slate-700">No medical cutoffs matched your filter criteria</span>
                          <span className="text-xs text-slate-500">Try adjusting your rank range, course, or category filters.</span>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    cutoffsData.items.map((row) => {
                      const isCompared = selectedForCompare.some((x) => x.id === row.id);
                      return (
                        <tr 
                          key={row.id} 
                          className="hover:bg-emerald-50/40 transition-colors group"
                        >
                          {/* College */}
                          <td className="py-3 px-4">
                            <div className="flex items-start gap-2.5">
                              <span className="mt-0.5 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-200">
                                {row.college_code}
                              </span>
                              <div>
                                <div className="font-semibold text-slate-900 group-hover:text-emerald-700 transition-colors">
                                  {row.college_name}
                                </div>
                                <div className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-2">
                                  <span className={`px-1.5 py-0.2 rounded text-[10px] ${
                                    row.college_type === 'Government/Aided' || row.college_type === 'AIIMS' || row.college_type === 'Central University'
                                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium' 
                                      : 'bg-slate-100 text-slate-600'
                                  }`}>
                                    {row.college_type || 'Medical College'}
                                  </span>
                                  {(row.city || row.state) && (
                                    <span>• {[row.city, row.state].filter(Boolean).join(', ')}</span>
                                  )}
                                </div>
                              </div>
                            </div>
                          </td>

                          {/* Course */}
                          <td className="py-3 px-3">
                            <span className="inline-block px-2 py-0.5 rounded text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                              {row.course_code}
                            </span>
                          </td>

                          {/* Quota / Category */}
                          <td className="py-3 px-3">
                            {(() => {
                              const q = row.quota_category || '';
                              const isWomen = (q.includes('(W)') || q.includes('Women') || (q.endsWith('W') && !['EWS', 'HEWS', 'PHEWS', 'PWD'].includes(q)) || q === 'W');
                              return (
                                <>
                                  <div className="flex items-center gap-1.5 flex-wrap">
                                    <span className="font-semibold text-slate-900">
                                      {row.quota_category}
                                    </span>
                                    {isWomen ? (
                                      <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-pink-50 text-pink-700 border border-pink-200">
                                        Women (30%)
                                      </span>
                                    ) : (
                                      <span className="text-[9px] font-medium uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                                        General
                                      </span>
                                    )}
                                  </div>
                                  <div className="text-[10px] text-slate-500 mt-0.5">
                                    Category: <span className="font-semibold text-slate-700">{row.base_category}</span>
                                  </div>
                                </>
                              );
                            })()}
                          </td>

                          {/* Closing AIR */}
                          <td className="py-3 px-3 text-right">
                            {row.closing_rank ? (
                              <div className="font-mono font-bold text-slate-900">
                                {formatNumber(row.closing_rank)}
                              </div>
                            ) : (
                              <span className="text-slate-400 font-mono">—</span>
                            )}
                            {row.opening_rank && row.opening_rank !== row.closing_rank && (
                              <div className="text-[10px] text-slate-400 font-mono">
                                Op: {formatNumber(row.opening_rank)}
                              </div>
                            )}
                          </td>

                          {/* NEET Marks */}
                          <td className="py-3 px-3 text-right">
                            {row.closing_score ? (
                              <div className="font-mono font-bold text-teal-700">
                                {row.closing_score}
                                <span className="text-[10px] text-slate-400 font-normal"> / 720</span>
                              </div>
                            ) : (
                              <span className="text-slate-400 font-mono">—</span>
                            )}
                            {row.opening_score && row.opening_score !== row.closing_score && (
                              <div className="text-[10px] text-slate-400 font-mono">
                                Op: {row.opening_score}
                              </div>
                            )}
                          </td>

                          {/* Round */}
                          <td className="py-3 px-3 text-center">
                            <span className="px-2 py-0.5 rounded text-[11px] bg-slate-100 text-slate-700 border border-slate-200">
                              {row.round}
                            </span>
                          </td>

                          {/* Year */}
                          <td className="py-3 px-3 text-center text-xs font-medium text-slate-700">
                            {row.academic_year}
                          </td>

                          {/* Chance */}
                          {rankParam && (
                            <td className="py-3 px-3 text-center">
                              {row.chance === 'High' && (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                                  High Chance
                                </span>
                              )}
                              {row.chance === 'Medium' && (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-teal-100 text-teal-800 border border-teal-200">
                                  Likely
                                </span>
                              )}
                              {row.chance === 'Borderline' && (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                                  Borderline
                                </span>
                              )}
                              {row.chance === 'Low' && (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200">
                                  Low Chance
                                </span>
                              )}
                            </td>
                          )}

                          {/* Compare Toggle */}
                          <td className="py-3 px-3 text-center">
                            <button
                              type="button"
                              onClick={() => toggleCompare(row)}
                              className={`p-1.5 rounded-lg text-xs transition-colors ${
                                isCompared 
                                  ? 'bg-emerald-600 text-white' 
                                  : 'text-slate-400 hover:bg-slate-100 hover:text-slate-800'
                              }`}
                              title={isCompared ? 'Remove from compare' : 'Add to compare'}
                            >
                              <Layers className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Table Pagination */}
            {cutoffsData && cutoffsData.total_pages > 1 && (
              <div className="p-4 border-t border-slate-200 bg-slate-50/50">
                <Pagination
                  page={cutoffsData.page}
                  pageSize={cutoffsData.page_size}
                  total={cutoffsData.total}
                  onPageChange={(p) => updateQueryParam('page', p.toString())}
                  onPageSizeChange={(sz) => updateQueryParam('page_size', sz.toString())}
                />
              </div>
            )}
          </div>
        )}

        {/* View Mode: Cards Grid (Light Theme) */}
        {viewMode === 'cards' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {isCutoffsLoading ? (
                <div className="col-span-full py-12 text-center text-slate-500">
                  <Spinner className="w-6 h-6 text-emerald-600" />
                </div>
              ) : !cutoffsData?.items || cutoffsData.items.length === 0 ? (
                <div className="col-span-full py-12 text-center text-slate-500">
                  No medical cutoffs found.
                </div>
              ) : (
                cutoffsData.items.map((row) => (
                  <div
                    key={row.id}
                    className="bg-white border border-slate-200 rounded-xl p-5 space-y-3.5 hover:border-emerald-400 hover:shadow-md transition-all shadow-xs relative"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                            {row.course_code}
                          </span>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                            Code {row.college_code}
                          </span>
                        </div>
                        <h4 className="text-sm font-bold text-slate-900 line-clamp-2 mt-1">
                          {row.college_name}
                        </h4>
                        {(row.city || row.state || row.college_type) && (
                          <p className="text-[11px] text-slate-500 mt-0.5">
                            {[row.college_type, [row.city, row.state].filter(Boolean).join(', ')].filter(Boolean).join(' • ')}
                          </p>
                        )}
                      </div>

                      <button
                        type="button"
                        onClick={() => toggleCompare(row)}
                        className="text-slate-400 hover:text-emerald-700"
                        title="Compare"
                      >
                        <Layers className="w-4 h-4" />
                      </button>
                    </div>

                    <div className="grid grid-cols-2 gap-2 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs font-mono">
                      <div>
                        <div className="text-[10px] font-sans text-slate-500 uppercase tracking-wider">Closing AIR</div>
                        <div className="text-base font-bold text-slate-900 mt-0.5">
                          {row.closing_rank ? formatNumber(row.closing_rank) : 'N/A'}
                        </div>
                      </div>

                      <div>
                        <div className="text-[10px] font-sans text-slate-500 uppercase tracking-wider">NEET Marks</div>
                        <div className="text-base font-bold text-teal-700 mt-0.5">
                          {row.closing_score ? `${row.closing_score} / 720` : 'N/A'}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
                      <div>
                        <span className="text-slate-700 font-medium">Quota:</span> {row.quota_category}
                      </div>
                      <div>
                        <span className="text-slate-700 font-medium">{row.round}</span> ({row.academic_year})
                      </div>
                    </div>

                    {row.chance && (
                      <div className="pt-2 border-t border-slate-100">
                        <div className={`text-center py-1 rounded-md text-xs font-semibold ${
                          row.chance === 'High' ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' :
                          row.chance === 'Medium' ? 'bg-teal-100 text-teal-800 border border-teal-200' :
                          row.chance === 'Borderline' ? 'bg-amber-100 text-amber-800 border border-amber-200' :
                          'bg-rose-100 text-rose-800 border border-rose-200'
                        }`}>
                          Chance: {row.chance}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* Cards Pagination */}
            {cutoffsData && cutoffsData.total_pages > 1 && (
              <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs">
                <Pagination
                  page={cutoffsData.page}
                  pageSize={cutoffsData.page_size}
                  total={cutoffsData.total}
                  onPageChange={(p) => updateQueryParam('page', p.toString())}
                  onPageSizeChange={(sz) => updateQueryParam('page_size', sz.toString())}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MedicalSearchPage;
