import React, { useState, useMemo, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import {
  getCsabFilterOptions,
  getCsabCutoffs,
  getCsabExportUrl,
  getCsabStats,
  resetCsabDatabase,
  scrapeCsabData,
  getCsabScraperStatus,
  CsabCutoff,
  CsabScraperStatus,
} from '../api/csab';
import {
  Search,
  RotateCcw,
  Building2,
  BookOpen,
  Download,
  LayoutGrid,
  Table as TableIcon,
  Award,
  CheckCircle2,
  ChevronRight,
  SlidersHorizontal,
  ExternalLink,
  ArrowUpDown,
  Filter,
  Sparkles,
  Trash2,
  RefreshCw,
  AlertTriangle,
  Globe,
  Building,
} from 'lucide-react';
import SearchableSelect, { SearchableOption } from '../components/ui/SearchableSelect';
import Select from '../components/ui/Select';
import Button from '../components/ui/Button';
import FilterChips, { ActiveFilter } from '../components/ui/FilterChips';
import Badge from '../components/ui/Badge';
import Spinner from '../components/ui/Spinner';
import toast from 'react-hot-toast';

export const CsabSearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const [showWipeModal, setShowWipeModal] = useState(false);
  const [showScraperModal, setShowScraperModal] = useState(false);
  const [pollScraper, setPollScraper] = useState(false);

  // Background Scraper Status Query with automatic 1-second polling while running
  const { data: scraperStatus } = useQuery<CsabScraperStatus>({
    queryKey: ['csabScraperStatus'],
    queryFn: getCsabScraperStatus,
    refetchInterval: (query) => {
      const data = query.state.data;
      return (data?.is_running || pollScraper) ? 1000 : false;
    },
  });

  // Automatically refresh filters and cutoffs when scraping completes
  const prevRunningRef = React.useRef(false);
  useEffect(() => {
    if (scraperStatus) {
      if (prevRunningRef.current && !scraperStatus.is_running) {
        setPollScraper(false);
        if (scraperStatus.status === 'COMPLETED') {
          toast.success('CSAB Special Round cutoffs scraped and ingested successfully!');
          queryClient.invalidateQueries({ queryKey: ['csabFilterOptions'] });
          queryClient.invalidateQueries({ queryKey: ['csabCutoffs'] });
          queryClient.invalidateQueries({ queryKey: ['csabStats'] });
        } else if (scraperStatus.status === 'FAILED') {
          toast.error(`CSAB scraping failed: ${scraperStatus.error || 'Check server connection'}`);
        }
      }
      prevRunningRef.current = scraperStatus.is_running;
    }
  }, [scraperStatus, queryClient]);

  const scraperMutation = useMutation({
    mutationFn: scrapeCsabData,
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message || 'CSAB scraper started in background!');
        setShowScraperModal(true);
        setPollScraper(true);
        queryClient.invalidateQueries({ queryKey: ['csabScraperStatus'] });
      } else {
        toast.error(data.message);
      }
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.message || 'Failed to start CSAB scraper');
    },
  });

  const wipeMutation = useMutation({
    mutationFn: resetCsabDatabase,
    onSuccess: (data) => {
      toast.success(data.message || 'CSAB database wiped successfully!');
      setShowWipeModal(false);
      queryClient.invalidateQueries({ queryKey: ['csabFilterOptions'] });
      queryClient.invalidateQueries({ queryKey: ['csabCutoffs'] });
      queryClient.invalidateQueries({ queryKey: ['csabStats'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.message || 'Failed to wipe CSAB database');
    },
  });

  // Helper to parse multi-value parameters safely
  const parseMultiParam = (param: string | null): string[] => {
    if (!param) return [];
    if (param.includes('||')) {
      return param.split('||').map((s) => s.trim()).filter(Boolean);
    }
    if (param.includes(',')) {
      return param.split(',').map((s) => s.trim()).filter(Boolean);
    }
    return [param.trim()].filter(Boolean);
  };

  // Filter states
  const [selectedRounds, setSelectedRounds] = useState<string[]>(() => {
    return parseMultiParam(searchParams.get('round'));
  });
  const [instituteType, setInstituteType] = useState<string>(searchParams.get('type') || '');
  const [selectedInstitutes, setSelectedInstitutes] = useState<string[]>(() => {
    return parseMultiParam(searchParams.get('institute'));
  });
  const [selectedStates, setSelectedStates] = useState<string[]>(() => {
    return parseMultiParam(searchParams.get('candidate_state') || searchParams.get('state'));
  });
  const [selectedPrograms, setSelectedPrograms] = useState<string[]>(() => {
    return parseMultiParam(searchParams.get('program'));
  });
  const [category, setCategory] = useState<string>(searchParams.get('category') || '');
  const [quota, setQuota] = useState<string>(searchParams.get('quota') || '');
  const [gender, setGender] = useState<string>(searchParams.get('gender') || '');
  const [academicYear, setAcademicYear] = useState<string>(searchParams.get('year') || '2026');
  const [maxRank, setMaxRank] = useState<string>(searchParams.get('max_rank') || '');
  const [page, setPage] = useState<number>(() => {
    const p = parseInt(searchParams.get('page') || '1', 10);
    return isNaN(p) || p < 1 ? 1 : p;
  });
  const [pageSize, setPageSize] = useState<number>(() => {
    const ps = parseInt(searchParams.get('page_size') || '100', 10);
    return isNaN(ps) ? 100 : ps;
  });
  const [sortBy, setSortBy] = useState<string>(searchParams.get('sort_by') || 'rank_asc');
  const [viewMode, setViewMode] = useState<'table' | 'card'>('table');

  // Fetch filter options
  const { data: filterOptions, isLoading: isFiltersLoading } = useQuery({
    queryKey: ['csabFilterOptions'],
    queryFn: getCsabFilterOptions,
    staleTime: 5 * 60 * 1000,
  });

  // Fetch DB stats
  const { data: dbStats } = useQuery({
    queryKey: ['csabStats'],
    queryFn: getCsabStats,
    staleTime: 60 * 1000,
  });

  // Keep URL in sync with filters
  useEffect(() => {
    const params = new URLSearchParams();
    if (selectedRounds.length > 0) params.set('round', selectedRounds.join(','));
    if (instituteType) params.set('type', instituteType);
    if (selectedInstitutes.length > 0) params.set('institute', selectedInstitutes.join('||'));
    if (selectedStates.length > 0) params.set('candidate_state', selectedStates.join(','));
    if (selectedPrograms.length > 0) params.set('program', selectedPrograms.join('||'));
    if (category) params.set('category', category);
    if (quota) params.set('quota', quota);
    if (gender) params.set('gender', gender);
    if (academicYear) params.set('year', academicYear);
    if (maxRank) params.set('max_rank', maxRank);
    if (page > 1) params.set('page', String(page));
    if (pageSize !== 100) params.set('page_size', String(pageSize));
    if (sortBy !== 'rank_asc') params.set('sort_by', sortBy);

    setSearchParams(params, { replace: true });
  }, [
    selectedRounds,
    instituteType,
    selectedInstitutes,
    selectedStates,
    selectedPrograms,
    category,
    quota,
    gender,
    academicYear,
    maxRank,
    page,
    pageSize,
    sortBy,
    setSearchParams,
  ]);

  // Query parameters for cutoffs API
  const cutoffParams = useMemo(() => {
    return {
      round_no: selectedRounds.length > 0 ? selectedRounds.join(',') : undefined,
      institute_type: instituteType || undefined,
      institute_name: selectedInstitutes.length > 0 ? selectedInstitutes.join('||') : undefined,
      candidate_state: selectedStates.length > 0 ? selectedStates.join(',') : undefined,
      academic_program: selectedPrograms.length > 0 ? selectedPrograms.join('||') : undefined,
      category: category || undefined,
      quota: quota || undefined,
      gender: gender || undefined,
      academic_year: academicYear ? parseInt(academicYear, 10) : undefined,
      max_rank: maxRank ? parseInt(maxRank, 10) : undefined,
      page,
      page_size: pageSize,
      sort_by: sortBy,
    };
  }, [
    selectedRounds,
    instituteType,
    selectedInstitutes,
    selectedStates,
    selectedPrograms,
    category,
    quota,
    gender,
    academicYear,
    maxRank,
    page,
    pageSize,
    sortBy,
  ]);

  // Fetch cutoffs
  const {
    data: cutoffResponse,
    isLoading: isCutoffsLoading,
    isFetching: isCutoffsFetching,
  } = useQuery({
    queryKey: ['csabCutoffs', cutoffParams],
    queryFn: () => getCsabCutoffs(cutoffParams),
    staleTime: 60 * 1000,
  });

  // Filter options mapping
  const roundSelectOptions: SearchableOption[] = useMemo(() => {
    const rounds = filterOptions?.rounds?.length ? filterOptions.rounds : [1, 2];
    return rounds.map((r) => ({
      value: String(r),
      label: `Special Round ${r}`,
    }));
  }, [filterOptions]);

  const instituteTypeOptions = useMemo(() => {
    const types = filterOptions?.institute_types || ['NIT', 'IIIT', 'IIEST', 'SPA', 'Other-GFTI'];
    return [
      { value: '', label: 'All Institute Types (NIT, IIIT, GFTI)' },
      ...types.map((t) => ({ value: t, label: t })),
    ];
  }, [filterOptions]);

  const instituteSelectOptions: SearchableOption[] = useMemo(() => {
    if (!filterOptions?.institutes) return [];
    let list = filterOptions.institutes;
    if (instituteType) {
      list = list.filter((i) => i.institute_type === instituteType);
    }
    return list.map((i) => ({
      value: i.institute_name,
      label: i.institute_name,
      badge: i.institute_type,
    }));
  }, [filterOptions, instituteType]);

  const stateSelectOptions: SearchableOption[] = useMemo(() => {
    if (!filterOptions?.states) return [];
    return filterOptions.states
      .filter(Boolean)
      .sort((a, b) => a.localeCompare(b))
      .map((s) => ({
        value: s,
        label: s,
      }));
  }, [filterOptions]);

  const programSelectOptions: SearchableOption[] = useMemo(() => {
    if (!filterOptions?.programs) return [];
    return filterOptions.programs.map((p) => ({
      value: p.program_name,
      label: p.program_name,
      badge: p.degree_type || undefined,
    }));
  }, [filterOptions]);

  const categoryOptions = useMemo(() => {
    if (!filterOptions?.categories) return [{ value: '', label: 'All Categories' }];
    return [
      { value: '', label: 'All Categories' },
      ...filterOptions.categories.map((c) => ({
        value: c.category_code,
        label: c.category_name && c.category_name !== c.category_code
          ? `${c.category_code} (${c.category_name})`
          : c.category_code,
      })),
    ];
  }, [filterOptions]);

  const quotaOptions = useMemo(() => {
    const quotas = filterOptions?.quotas || ['AI', 'HS', 'OS', 'GO', 'JK', 'LA'];
    return [
      { value: '', label: 'All Quotas (AI, HS, OS)' },
      ...quotas.map((q) => ({
        value: q,
        label:
          q === 'AI'
            ? 'AI (All India)'
            : q === 'HS'
            ? 'HS (Home State)'
            : q === 'OS'
            ? 'OS (Other State)'
            : q,
      })),
    ];
  }, [filterOptions]);

  const genderOptions = useMemo(() => {
    return [
      { value: '', label: 'All Seat Pools' },
      { value: 'Gender-Neutral', label: 'Gender-Neutral' },
      { value: 'Female-only', label: 'Female-only (incl. Supernumerary)' },
    ];
  }, []);

  const handleResetFilters = () => {
    setSelectedRounds([]);
    setInstituteType('');
    setSelectedInstitutes([]);
    setSelectedStates([]);
    setSelectedPrograms([]);
    setCategory('');
    setQuota('');
    setGender('');
    setAcademicYear('2026');
    setMaxRank('');
    setPage(1);
    setSortBy('rank_asc');
  };

  // Active filter chips
  const activeFilters: ActiveFilter[] = useMemo(() => {
    const list: ActiveFilter[] = [];
    selectedRounds.forEach((r) => {
      list.push({ id: `round:${r}`, label: 'Round', value: `Special Round ${r}` });
    });
    if (instituteType) {
      list.push({ id: 'type', label: 'Type', value: instituteType });
    }
    selectedInstitutes.forEach((inst) => {
      list.push({ id: `institute:${inst}`, label: 'Institute', value: inst });
    });
    selectedStates.forEach((st) => {
      list.push({ id: `state:${st}`, label: 'Home State', value: st });
    });
    selectedPrograms.forEach((prog) => {
      list.push({ id: `program:${prog}`, label: 'Program', value: prog });
    });
    if (category) list.push({ id: 'category', label: 'Category', value: category });
    if (quota) list.push({ id: 'quota', label: 'Quota', value: quota });
    if (gender) list.push({ id: 'gender', label: 'Seat Pool', value: gender });
    if (maxRank) list.push({ id: 'rank', label: 'CRL Rank ≤', value: `#${Number(maxRank).toLocaleString()}` });
    return list;
  }, [
    selectedRounds,
    instituteType,
    selectedInstitutes,
    selectedStates,
    selectedPrograms,
    category,
    quota,
    gender,
    maxRank,
  ]);

  const removeFilterChip = (id: string) => {
    if (id.startsWith('round:')) {
      const val = id.substring('round:'.length);
      setSelectedRounds((prev) => prev.filter((item) => item !== val));
      return;
    }
    if (id === 'type') setInstituteType('');
    if (id.startsWith('institute:')) {
      const val = id.substring('institute:'.length);
      setSelectedInstitutes((prev) => prev.filter((item) => item !== val));
      return;
    }
    if (id.startsWith('state:')) {
      const val = id.substring('state:'.length);
      setSelectedStates((prev) => prev.filter((item) => item !== val));
      return;
    }
    if (id.startsWith('program:')) {
      const val = id.substring('program:'.length);
      setSelectedPrograms((prev) => prev.filter((item) => item !== val));
      return;
    }
    if (id === 'category') setCategory('');
    if (id === 'quota') setQuota('');
    if (id === 'gender') setGender('');
    if (id === 'rank') setMaxRank('');
  };

  const candidateRankNum = maxRank ? parseInt(maxRank, 10) : null;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-teal-500/10 text-teal-700 border border-teal-500/20">
                CSAB SPECIAL ROUNDS
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                NITs, IIITs, IIEST, SPAs & GFTIs
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700">
                Cycle 2026
              </span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
              <Building className="w-6 h-6 text-teal-600" />
              CSAB Special Round Cutoff Explorer
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Official Opening & Closing Common Rank List (CRL) Ranks across CSAB Special Round 1 and Round 2 for vacant seat allocation.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Scraper Status Badge */}
            {scraperStatus?.is_running && (
              <button
                type="button"
                onClick={() => setShowScraperModal(true)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold bg-teal-50 text-teal-700 border border-teal-200 animate-pulse hover:bg-teal-100"
              >
                <Spinner className="w-4 h-4 text-teal-600" />
                <span>
                  Scraping Round {scraperStatus.current_round || 1} ({scraperStatus.progress_percent}%)
                </span>
              </button>
            )}

            {/* Trigger Live Scrape */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => scraperMutation.mutate()}
              disabled={scraperMutation.isPending || scraperStatus?.is_running}
              className="text-xs font-bold border-teal-300 text-teal-700 hover:bg-teal-50"
            >
              <Globe className="w-3.5 h-3.5 mr-1.5 text-teal-600" />
              {scraperStatus?.is_running ? 'Scraper Running...' : 'Web Scrape CSAB'}
            </Button>

            {/* Wipe Database Button */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowWipeModal(true)}
              className="text-xs font-medium text-rose-600 border-rose-200 hover:bg-rose-50"
            >
              <Trash2 className="w-3.5 h-3.5 mr-1.5" />
              Wipe DB
            </Button>

            {/* CSV Export */}
            <a
              href={getCsabExportUrl(cutoffParams)}
              download
              className="inline-flex items-center justify-center px-3.5 py-1.5 rounded-lg text-xs font-bold bg-teal-600 text-white shadow-sm hover:bg-teal-700 transition-colors"
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              Export CSV
            </a>
          </div>
        </div>
      </div>

      {/* Database Status Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm text-slate-300">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${dbStats && dbStats.total_cutoffs > 0 ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
            <div>
              <div className="text-xs font-bold text-white flex items-center gap-2">
                <span>CSAB Standalone SQLite Database (csab.db)</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-teal-300 border border-slate-700">
                  {dbStats && dbStats.total_cutoffs > 0 ? 'Live Connected' : 'Ready to Scrape'}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                {dbStats && dbStats.total_cutoffs > 0 ? (
                  <>
                    <strong className="text-slate-200">{dbStats.total_cutoffs.toLocaleString()}</strong> cutoffs recorded across{' '}
                    <strong className="text-slate-200">{dbStats.total_institutes}</strong> institutes and{' '}
                    <strong className="text-slate-200">{dbStats.total_programs}</strong> programs (Special Rounds 1 & 2).
                  </>
                ) : (
                  'No CSAB cutoffs loaded yet. Click "Web Scrape CSAB" to extract Special Round 1 and Round 2 data directly from admissions.nic.in.'
                )}
              </p>
            </div>
          </div>

          {(!dbStats || dbStats.total_cutoffs === 0) && (
            <Button
              size="sm"
              onClick={() => scraperMutation.mutate()}
              disabled={scraperMutation.isPending || scraperStatus?.is_running}
              className="text-xs font-bold bg-teal-600 hover:bg-teal-700 text-white shadow-sm flex-shrink-0"
            >
              <Globe className="w-3.5 h-3.5 mr-1.5" />
              Start Web Scraper
            </Button>
          )}
        </div>
      </div>

      {/* Multi-Panel Switcher Navigation */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 shadow-md">
        <div className="flex flex-col md:flex-row items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2 bg-slate-950/90 p-1.5 rounded-lg border border-slate-800 w-full md:w-auto">
            <Link
              to="/search?panel=state"
              className="flex-1 md:flex-initial flex items-center justify-center gap-2 px-4 py-2 rounded-md text-xs font-bold text-slate-400 hover:text-white hover:bg-slate-800/80 transition-all"
            >
              <Building2 className="w-4 h-4 text-primary-400" />
              <span>MHT-CET (State)</span>
            </Link>

            <Link
              to="/search?panel=all_india"
              className="flex-1 md:flex-initial flex items-center justify-center gap-2 px-4 py-2 rounded-md text-xs font-bold text-slate-400 hover:text-white hover:bg-slate-800/80 transition-all"
            >
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <span>MHT-CET (All India)</span>
            </Link>

            <Link
              to="/josaa"
              className="flex-1 md:flex-initial flex items-center justify-center gap-2 px-4 py-2 rounded-md text-xs font-bold text-slate-400 hover:text-white hover:bg-slate-800/80 transition-all"
            >
              <Award className="w-4 h-4 text-amber-400" />
              <span>JoSAA (IIT / NIT / IIIT)</span>
            </Link>

            <div className="flex-1 md:flex-initial flex items-center justify-center gap-2 px-4 py-2 rounded-md text-xs font-bold bg-teal-500/20 text-teal-300 shadow-sm ring-1 ring-teal-500/50">
              <Building className="w-4 h-4 text-teal-400" />
              <span>CSAB Special (NIT / IIIT)</span>
              <span className="ml-1 text-[10px] bg-teal-500/30 text-teal-200 px-2 py-0.5 rounded-full border border-teal-400/40">
                Active Panel
              </span>
            </div>
          </div>

          <div className="text-right px-2 hidden lg:block">
            <span className="text-xs font-bold text-slate-200">
              ⚡ Vacant Seats Allotment
            </span>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Central Seat Allocation Board Special Rounds
            </p>
          </div>
        </div>
      </div>

      {/* Info Callout */}
      <div className="bg-teal-50 border border-teal-200 rounded-xl p-4 text-teal-900">
        <div className="flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-teal-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <p className="font-bold text-teal-950">
              Important: All CSAB Cutoffs are All-India Common Rank List (CRL) Ranks
            </p>
            <p className="text-teal-800">
              Unlike JoSAA where category ranks are reported, in CSAB Special Rounds all opening and closing ranks for all categories (including OBC-NCL, SC, ST, GEN-EWS) represent Common Rank List (CRL) ranks. These ranks include fresh allotments and candidates upgraded from JoSAA Round 5.
            </p>
          </div>
        </div>
      </div>

      {/* Filter Section */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-4 bg-slate-50/70 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-slate-600" />
            <span className="text-sm font-semibold text-slate-800">Special Round Search Filters</span>
          </div>
          <div className="text-xs text-slate-500">
            Exact CRL Ranks (Opening & Closing)
          </div>
        </div>

        <div className="p-5 space-y-4">
          {/* Row 1: Special Round, Institute Type, Category, Quota */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <SearchableSelect
              label="CSAB Special Round"
              placeholder="All Special Rounds"
              multiple={true}
              values={selectedRounds}
              onMultiChange={setSelectedRounds}
              options={roundSelectOptions}
              helperText={
                selectedRounds.length > 0
                  ? `${selectedRounds.length} round(s) selected`
                  : 'Multi-select Round 1 or Round 2'
              }
            />

            <Select
              label="Institute Type"
              value={instituteType}
              onChange={(e) => setInstituteType(e.target.value)}
              options={instituteTypeOptions}
            />

            <Select
              label="Seat Category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              options={categoryOptions}
            />

            <Select
              label="Seat Quota"
              value={quota}
              onChange={(e) => setQuota(e.target.value)}
              options={quotaOptions}
            />
          </div>

          {/* Row 2: Institute Name & Branch Name */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <SearchableSelect
              label="Participating Institute"
              placeholder="Search & multi-select NITs, IIITs, IIEST, GFTIs..."
              multiple={true}
              values={selectedInstitutes}
              onMultiChange={setSelectedInstitutes}
              options={instituteSelectOptions}
              helperText={
                selectedInstitutes.length > 0
                  ? `${selectedInstitutes.length} institute(s) selected`
                  : 'Filter by specific institutes'
              }
            />

            <SearchableSelect
              label="Academic Program / Branch"
              placeholder="Search branches (Computer Science, Electrical, Mechanical...)"
              multiple={true}
              values={selectedPrograms}
              onMultiChange={setSelectedPrograms}
              options={programSelectOptions}
              helperText={
                selectedPrograms.length > 0
                  ? `${selectedPrograms.length} program(s) selected`
                  : 'Filter by engineering branches'
              }
            />
          </div>

          {/* Row 3: Candidate Home State, Gender, CRL Rank, Sort By */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <SearchableSelect
              label="Candidate Home State (HS vs OS)"
              placeholder="Select your Home State..."
              multiple={true}
              values={selectedStates}
              onMultiChange={setSelectedStates}
              options={stateSelectOptions}
              helperText="Resolves HS quota vs OS quota eligibility"
            />

            <Select
              label="Seat Pool / Gender"
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              options={genderOptions}
            />

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Your JEE Main CRL Rank
              </label>
              <div className="relative">
                <input
                  type="number"
                  placeholder="e.g. 15420"
                  value={maxRank}
                  onChange={(e) => {
                    setMaxRank(e.target.value);
                    setPage(1);
                  }}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                />
              </div>
              <p className="text-[10px] text-slate-400 mt-1">
                Filters options where Closing Rank &ge; your rank
              </p>
            </div>

            <Select
              label="Sort Results By"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              options={[
                { value: 'rank_asc', label: 'Closing Rank: Lowest to Highest' },
                { value: 'rank_desc', label: 'Closing Rank: Highest to Lowest' },
                { value: 'opening_rank_asc', label: 'Opening Rank: Lowest to Highest' },
                { value: 'institute', label: 'Institute Name (A-Z)' },
                { value: 'program', label: 'Program Name (A-Z)' },
              ]}
            />
          </div>

          {/* Active Filter Chips */}
          <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <FilterChips
              filters={activeFilters}
              onRemove={removeFilterChip}
              onClearAll={handleResetFilters}
            />

            <div className="flex items-center gap-2 self-end sm:self-auto">
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetFilters}
                className="text-xs"
              >
                <RotateCcw className="w-3.5 h-3.5 mr-1" />
                Reset Filters
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Results Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl shadow-sm border border-slate-200">
        <div className="flex items-center gap-3">
          <div className="text-sm font-bold text-slate-800">
            {isCutoffsLoading ? (
              <span className="flex items-center gap-2 text-slate-500">
                <Spinner className="w-4 h-4 text-slate-500" />
                Searching CSAB cutoffs...
              </span>
            ) : (
              <span>
                Found <span className="text-teal-600 font-extrabold">{cutoffResponse?.total.toLocaleString() || 0}</span> matching cutoff records
              </span>
            )}
          </div>
          {isCutoffsFetching && !isCutoffsLoading && (
            <Spinner className="w-4 h-4 text-teal-600" />
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200">
            <button
              type="button"
              onClick={() => setViewMode('table')}
              className={`p-1.5 rounded-md text-xs font-medium transition-all ${
                viewMode === 'table'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
              title="Table View"
            >
              <TableIcon className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode('card')}
              className={`p-1.5 rounded-md text-xs font-medium transition-all ${
                viewMode === 'card'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
              title="Card View"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
          </div>

          {/* Page Size Select */}
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
            }}
            className="px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-700 focus:ring-1 focus:ring-teal-500"
          >
            <option value="50">50 / page</option>
            <option value="100">100 / page</option>
            <option value="250">250 / page</option>
            <option value="500">500 / page</option>
          </select>
        </div>
      </div>

      {/* Results Content */}
      {isCutoffsLoading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-16 flex flex-col items-center justify-center text-center">
          <Spinner className="w-8 h-8 text-teal-600 mb-3" />
          <h3 className="text-sm font-bold text-slate-800">Loading CSAB Special Round Cutoffs...</h3>
          <p className="text-xs text-slate-500 mt-1">Querying opening and closing CRL ranks</p>
        </div>
      ) : !cutoffResponse || cutoffResponse.items.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-16 text-center">
          <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mx-auto mb-3">
            <Search className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold text-slate-800">No CSAB Cutoff Records Found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            {dbStats && dbStats.total_cutoffs > 0
              ? 'Try widening your filters, clearing the rank restriction, or resetting search options.'
              : 'The CSAB database is currently empty. Click "Web Scrape CSAB" at the top to scrape Special Round 1 and Round 2 cutoffs from admissions.nic.in.'}
          </p>
          <div className="mt-4 flex items-center justify-center gap-2">
            <Button size="sm" variant="outline" onClick={handleResetFilters} className="text-xs">
              Reset Filters
            </Button>
            {(!dbStats || dbStats.total_cutoffs === 0) && (
              <Button
                size="sm"
                onClick={() => scraperMutation.mutate()}
                className="text-xs bg-teal-600 text-white"
              >
                Web Scrape Now
              </Button>
            )}
          </div>
        </div>
      ) : viewMode === 'table' ? (
        /* Table View */
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-4">Round</th>
                  <th className="py-3 px-4">Institute</th>
                  <th className="py-3 px-4">Academic Program</th>
                  <th className="py-3 px-4">Quota</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Seat Pool</th>
                  <th className="py-3 px-4 text-right">Opening CRL</th>
                  <th className="py-3 px-4 text-right">Closing CRL</th>
                  {candidateRankNum && <th className="py-3 px-4 text-center">Status</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {cutoffResponse.items.map((row: CsabCutoff) => {
                  const isEligible = candidateRankNum ? candidateRankNum <= row.closing_rank : null;
                  const isSafe = candidateRankNum ? candidateRankNum <= row.opening_rank : false;

                  return (
                    <tr
                      key={row.id}
                      className="hover:bg-teal-50/40 transition-colors"
                    >
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-100 text-teal-800 border border-teal-200">
                          Special R{row.round_no}
                        </span>
                      </td>
                      <td className="py-3 px-4 max-w-xs">
                        <div className="font-semibold text-slate-900 truncate" title={row.institute_name}>
                          {row.institute_name}
                        </div>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className="text-[10px] px-1.5 py-0.2 rounded font-medium bg-slate-100 text-slate-600">
                            {row.institute_type}
                          </span>
                          {row.institute_state && (
                            <span className="text-[10px] text-slate-500">
                              {row.institute_state}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 max-w-md">
                        <div className="font-medium text-slate-900 leading-snug">
                          {row.program_name}
                        </div>
                        {row.degree_type && (
                          <span className="text-[10px] text-slate-500 font-medium">
                            {row.degree_type}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          row.quota === 'AI'
                            ? 'bg-purple-100 text-purple-700'
                            : row.quota === 'HS'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-amber-100 text-amber-700'
                        }`}>
                          {row.quota}
                        </span>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap font-bold text-slate-800">
                        {row.category_code}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap text-slate-600">
                        {row.gender}
                      </td>
                      <td className="py-3 px-4 text-right whitespace-nowrap font-mono text-emerald-700 font-bold">
                        {row.opening_rank.toLocaleString()}
                        {row.is_preparatory ? <span className="text-amber-600 text-[10px] ml-0.5">P</span> : ''}
                      </td>
                      <td className="py-3 px-4 text-right whitespace-nowrap font-mono text-teal-700 font-black text-sm">
                        {row.closing_rank.toLocaleString()}
                        {row.is_preparatory ? <span className="text-amber-600 text-[10px] ml-0.5">P</span> : ''}
                      </td>
                      {candidateRankNum && (
                        <td className="py-3 px-4 text-center whitespace-nowrap">
                          {isSafe ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                              Safe
                            </span>
                          ) : isEligible ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-100 text-teal-800 border border-teal-200">
                              In Reach
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-500">
                              Closed
                            </span>
                          )}
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* Card View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cutoffResponse.items.map((row: CsabCutoff) => {
            const isEligible = candidateRankNum ? candidateRankNum <= row.closing_rank : null;
            const isSafe = candidateRankNum ? candidateRankNum <= row.opening_rank : false;

            return (
              <div
                key={row.id}
                className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 hover:border-teal-300 hover:shadow-md transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-100 text-teal-800 border border-teal-200">
                      Special Round {row.round_no}
                    </span>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                      {row.institute_type}
                    </span>
                  </div>

                  <h4 className="text-xs font-bold text-slate-900 line-clamp-2" title={row.institute_name}>
                    {row.institute_name}
                  </h4>
                  {row.institute_state && (
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      {row.institute_state}
                    </p>
                  )}

                  <div className="mt-2.5 p-2 bg-slate-50 rounded-lg border border-slate-100">
                    <p className="text-xs font-medium text-slate-800 leading-snug line-clamp-2">
                      {row.program_name}
                    </p>
                    <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-500">
                      <span>Quota: <strong className="text-slate-700">{row.quota}</strong></span>
                      <span>&bull;</span>
                      <span>Cat: <strong className="text-slate-700">{row.category_code}</strong></span>
                      <span>&bull;</span>
                      <span>{row.gender}</span>
                    </div>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-slate-400 block uppercase font-semibold">Opening CRL</span>
                    <span className="text-xs font-mono font-bold text-emerald-700">
                      {row.opening_rank.toLocaleString()}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 block uppercase font-semibold">Closing CRL</span>
                    <span className="text-sm font-mono font-black text-teal-700">
                      {row.closing_rank.toLocaleString()}
                    </span>
                  </div>
                </div>

                {candidateRankNum && (
                  <div className="mt-2 pt-2 border-t border-slate-100 text-center">
                    {isSafe ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                        Safe Choice (Rank {candidateRankNum.toLocaleString()} &le; {row.opening_rank.toLocaleString()})
                      </span>
                    ) : isEligible ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-100 text-teal-800">
                        In Reach (Rank {candidateRankNum.toLocaleString()} &le; {row.closing_rank.toLocaleString()})
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-500">
                        Closed at {row.closing_rank.toLocaleString()}
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {cutoffResponse && cutoffResponse.total_pages > 1 && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="text-xs text-slate-600">
            Showing Page <strong className="text-slate-900">{page}</strong> of{' '}
            <strong className="text-slate-900">{cutoffResponse.total_pages}</strong> ({cutoffResponse.total.toLocaleString()} cutoffs)
          </div>

          <div className="flex items-center gap-1.5">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(1)}
              disabled={page <= 1}
              className="text-xs px-2.5 py-1"
            >
              First
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="text-xs px-3 py-1"
            >
              Previous
            </Button>

            <span className="px-3 py-1 text-xs font-bold text-teal-700 bg-teal-50 rounded-lg border border-teal-200">
              {page}
            </span>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(cutoffResponse.total_pages, p + 1))}
              disabled={page >= cutoffResponse.total_pages}
              className="text-xs px-3 py-1"
            >
              Next
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(cutoffResponse.total_pages)}
              disabled={page >= cutoffResponse.total_pages}
              className="text-xs px-2.5 py-1"
            >
              Last
            </Button>
          </div>
        </div>
      )}

      {/* Live Scraper Progress Modal */}
      {showScraperModal && scraperStatus && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Globe className="w-5 h-5 text-teal-600" />
                <h3 className="text-base font-bold text-slate-900">
                  CSAB Official Portal Web Scraper
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowScraperModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                &times;
              </button>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Scraping Special Round 1 and Round 2 Opening &amp; Closing CRL Ranks live from the official NIC portal (<code className="text-teal-700 bg-teal-50 px-1 py-0.5 rounded">admissions.nic.in/csabspl</code>).
            </p>

            {/* Progress Bar */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700">
                  {scraperStatus.status === 'COMPLETED'
                    ? 'Scraping Completed'
                    : scraperStatus.status === 'FAILED'
                    ? 'Scraping Failed'
                    : `Special Round ${scraperStatus.current_round || 1} of 2`}
                </span>
                <span className="font-bold text-teal-700">{scraperStatus.progress_percent}%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden border border-slate-200">
                <div
                  className="bg-gradient-to-r from-teal-500 to-emerald-500 h-full rounded-full transition-all duration-300"
                  style={{ width: `${scraperStatus.progress_percent}%` }}
                />
              </div>
            </div>

            {/* Telemetry Details */}
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Status:</span>
                <span className="font-bold text-slate-800">{scraperStatus.status}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Special Round 1 Records:</span>
                <span className="font-mono font-bold text-teal-700">
                  {scraperStatus.records_round1.toLocaleString()}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Special Round 2 Records:</span>
                <span className="font-mono font-bold text-teal-700">
                  {scraperStatus.records_round2.toLocaleString()}
                </span>
              </div>
              <div className="flex items-center justify-between border-t border-slate-200 pt-1.5">
                <span className="text-slate-700 font-semibold">Total CSAB Records:</span>
                <span className="font-mono font-extrabold text-teal-800">
                  {scraperStatus.total_records.toLocaleString()}
                </span>
              </div>
            </div>

            {/* Stage Message */}
            <p className="text-xs text-slate-600 bg-teal-50/60 p-2.5 rounded-lg border border-teal-100 italic">
              {scraperStatus.message}
            </p>

            <div className="flex justify-end pt-2">
              <Button
                size="sm"
                onClick={() => setShowScraperModal(false)}
                className="text-xs bg-slate-900 text-white"
              >
                {scraperStatus.is_running ? 'Keep Scraping in Background' : 'Close'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Wipe Database Modal */}
      {showWipeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center gap-2 text-rose-600">
              <AlertTriangle className="w-5 h-5" />
              <h3 className="text-base font-bold text-slate-900">Reset CSAB Database</h3>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Are you sure you want to wipe all records from <code className="font-mono font-bold text-slate-800">csab.db</code>? All cutoff records, programs, categories, and institutes will be deleted. You can re-scrape the data anytime.
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowWipeModal(false)}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => wipeMutation.mutate()}
                disabled={wipeMutation.isPending}
                className="text-xs bg-rose-600 hover:bg-rose-700 text-white"
              >
                {wipeMutation.isPending ? 'Wiping...' : 'Yes, Wipe Database'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CsabSearchPage;
