import React, { useState, useMemo, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  getJosaaFilterOptions, 
  getJosaaCutoffs, 
  getJosaaExportUrl,
  JosaaCutoff 
} from '../api/josaa';
import { 
  Search, RotateCcw, Building2, BookOpen, 
  Download, LayoutGrid, Table as TableIcon,
  Award, CheckCircle2, ChevronRight, SlidersHorizontal,
  ExternalLink, ArrowUpDown, Filter, Sparkles,
  Trash2, RefreshCw, AlertTriangle, Globe
} from 'lucide-react';
import SearchableSelect, { SearchableOption } from '../components/ui/SearchableSelect';
import Select from '../components/ui/Select';
import Button from '../components/ui/Button';
import FilterChips, { ActiveFilter } from '../components/ui/FilterChips';
import Badge from '../components/ui/Badge';
import Spinner from '../components/ui/Spinner';
import toast from 'react-hot-toast';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { 
  resetJosaaDatabase, 
  reloadJosaaData, 
  scrapeJosaaData, 
  getJosaaScraperStatus,
  JosaaScraperStatus 
} from '../api/josaa';

export const JosaaSearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const [showWipeModal, setShowWipeModal] = useState(false);
  const [showScraperModal, setShowScraperModal] = useState(false);
  const [pollScraper, setPollScraper] = useState(false);

  // Background Scraper Status Query with automatic 1-second polling while running
  const { data: scraperStatus } = useQuery<JosaaScraperStatus>({
    queryKey: ['josaaScraperStatus'],
    queryFn: getJosaaScraperStatus,
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
          toast.success('JoSAA cutoffs for Years 2025 & 2026 scraped and ingested successfully!');
          queryClient.invalidateQueries({ queryKey: ['josaaFilterOptions'] });
          queryClient.invalidateQueries({ queryKey: ['josaaCutoffs'] });
          queryClient.invalidateQueries({ queryKey: ['josaaStats'] });
        } else if (scraperStatus.status === 'FAILED') {
          toast.error(`JoSAA scraping failed: ${scraperStatus.error || 'Check server connection'}`);
        }
      }
      prevRunningRef.current = scraperStatus.is_running;
    }
  }, [scraperStatus, queryClient]);

  const scraperMutation = useMutation({
    mutationFn: scrapeJosaaData,
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message || 'JoSAA scraper started in background!');
        setShowScraperModal(true);
        setPollScraper(true);
        queryClient.invalidateQueries({ queryKey: ['josaaScraperStatus'] });
      } else {
        toast.error(data.message);
      }
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.message || 'Failed to start JoSAA scraper');
    }
  });

  const wipeMutation = useMutation({
    mutationFn: resetJosaaDatabase,
    onSuccess: (data) => {
      toast.success(data.message || 'JoSAA database wiped successfully!');
      setShowWipeModal(false);
      queryClient.invalidateQueries({ queryKey: ['josaaFilterOptions'] });
      queryClient.invalidateQueries({ queryKey: ['josaaCutoffs'] });
      queryClient.invalidateQueries({ queryKey: ['josaaStats'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.message || 'Failed to wipe JoSAA database');
    }
  });

  const reloadMutation = useMutation({
    mutationFn: scrapeJosaaData,
    onSuccess: (data) => {
      toast.success(data.message || 'JoSAA web scraping started!');
      setShowScraperModal(true);
      setPollScraper(true);
      queryClient.invalidateQueries({ queryKey: ['josaaScraperStatus'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.message || 'Failed to start JoSAA scraper');
    }
  });

  // Helper to parse multi-value parameters safely without breaking names with commas
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
  const [candidateRank, setCandidateRank] = useState<string>(searchParams.get('rank') || '');

  // UI state
  const [hasSearched, setHasSearched] = useState(true);
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');
  const [sortBy, setSortBy] = useState<'rank_asc' | 'rank_desc' | 'opening_rank_asc' | 'institute' | 'program'>('rank_asc');
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(50);

  // Sync from URL params on load
  useEffect(() => {
    const roundParam = searchParams.get('round');
    const typeParam = searchParams.get('type');
    const instParam = searchParams.get('institute');
    const stateParam = searchParams.get('candidate_state') || searchParams.get('state');
    const progParam = searchParams.get('program');
    const catParam = searchParams.get('category');
    const quotaParam = searchParams.get('quota');
    const genParam = searchParams.get('gender');
    const yrParam = searchParams.get('year');
    const rkParam = searchParams.get('rank');

    const hasAny = Boolean(roundParam || typeParam || instParam || stateParam || progParam || catParam || quotaParam || genParam || yrParam || rkParam);
    if (hasAny) {
      if (roundParam !== null) setSelectedRounds(parseMultiParam(roundParam));
      if (typeParam !== null) setInstituteType(typeParam);
      if (instParam !== null) setSelectedInstitutes(parseMultiParam(instParam));
      if (stateParam !== null) setSelectedStates(parseMultiParam(stateParam));
      if (progParam !== null) setSelectedPrograms(parseMultiParam(progParam));
      if (catParam !== null) setCategory(catParam);
      if (quotaParam !== null) setQuota(quotaParam);
      if (genParam !== null) setGender(genParam);
      if (yrParam !== null) setAcademicYear(yrParam);
      if (rkParam !== null) setCandidateRank(rkParam);
      setHasSearched(true);
    }
  }, [searchParams]);

  // Load filter options from JoSAA DB
  const { data: filterOptions, isLoading: isOptionsLoading } = useQuery({
    queryKey: ['josaaFilterOptions'],
    queryFn: getJosaaFilterOptions,
    staleTime: 300000,
  });

  // Default year to latest available year
  useEffect(() => {
    if (filterOptions?.years?.length && !searchParams.get('year')) {
      setAcademicYear(filterOptions.years[0].toString());
    }
  }, [filterOptions, searchParams]);

  // Prepare State options (Candidate Home States for HS & OS quota eligibility)
  const stateOptions: SearchableOption[] = useMemo(() => {
    const list: SearchableOption[] = [];
    if (filterOptions?.states && filterOptions.states.length > 0) {
      filterOptions.states.forEach((st) => {
        list.push({
          value: st,
          label: st,
          sublabel: 'State of Eligibility',
        });
      });
    }
    return list;
  }, [filterOptions]);

  // Prepare Institute options (optionally filtered by instituteType)
  const instituteOptions: SearchableOption[] = useMemo(() => {
    const list: SearchableOption[] = [];
    if (filterOptions?.institutes) {
      filterOptions.institutes.forEach((inst) => {
        if (!instituteType || inst.institute_type === instituteType) {
          list.push({
            value: inst.institute_name,
            label: inst.institute_name,
            sublabel: `${inst.institute_type} • ${inst.state || 'India'}${inst.institute_code ? ` • Code: ${inst.institute_code}` : ''}`,
          });
        }
      });
    }
    return list;
  }, [filterOptions, instituteType]);

  // Prepare Program options
  const programOptions: SearchableOption[] = useMemo(() => {
    const list: SearchableOption[] = [];
    if (filterOptions?.programs) {
      filterOptions.programs.forEach((prog) => {
        list.push({
          value: prog.program_name,
          label: prog.program_name,
          sublabel: prog.degree_type ? `Degree: ${prog.degree_type}` : undefined,
        });
      });
    }
    return list;
  }, [filterOptions]);

  // JoSAA Rounds dropdown options
  const roundSelectOptions = useMemo(() => {
    const list = [{ value: '', label: 'All JoSAA Rounds' }];
    const roundsList = (filterOptions?.rounds && filterOptions.rounds.length > 0)
      ? filterOptions.rounds
      : [1, 2, 3, 4, 5, 6];
    roundsList.forEach((r) => {
      list.push({ value: String(r), label: `Round ${r}` });
    });
    return list;
  }, [filterOptions]);

  // Institute Type dropdown options
  const instituteTypeOptions = useMemo(() => {
    const list = [{ value: '', label: 'All Institute Types (IIT, NIT, IIIT, GFTI)' }];
    if (filterOptions?.institute_types) {
      filterOptions.institute_types.forEach((t) => {
        let label = t;
        if (t === 'IIT') label = 'IIT (Indian Institutes of Technology)';
        else if (t === 'NIT') label = 'NIT (National Institutes of Technology)';
        else if (t === 'IIIT') label = 'IIIT (Indian Institutes of Information Technology)';
        else if (t === 'Other-GFTI') label = 'Other-GFTI (Govt Funded Technical Institutes)';
        list.push({ value: t, label });
      });
    } else {
      list.push(
        { value: 'IIT', label: 'IIT (Indian Institutes of Technology)' },
        { value: 'NIT', label: 'NIT (National Institutes of Technology)' },
        { value: 'IIIT', label: 'IIIT (Indian Institutes of Information Technology)' },
        { value: 'Other-GFTI', label: 'Other-GFTI (Govt Funded Technical Institutes)' }
      );
    }
    return list;
  }, [filterOptions]);

  // Category dropdown options
  const categoryOptions = useMemo(() => {
    const list = [{ value: '', label: 'All Categories' }];
    if (filterOptions?.categories) {
      filterOptions.categories.forEach((c) => {
        list.push({
          value: c.category_code,
          label: c.category_name ? `${c.category_code} (${c.category_name})` : c.category_code,
        });
      });
    }
    return list;
  }, [filterOptions]);

  // Quota options with descriptive labels
  const quotaOptions = useMemo(() => {
    const list = [{ value: '', label: 'All Quotas (AI, HS, OS, GO, JK, LA)' }];
    const allQuotas = (filterOptions?.quotas && filterOptions.quotas.length > 0)
      ? filterOptions.quotas
      : ['AI', 'HS', 'OS', 'GO', 'JK', 'LA'];

    allQuotas.forEach((q) => {
      let label = q;
      if (q === 'AI') label = 'AI (All India Quota)';
      else if (q === 'HS') label = 'HS (Home State Quota)';
      else if (q === 'OS') label = 'OS (Other State Quota)';
      else if (q === 'GO') label = 'GO (Goa State Quota - NIT Goa)';
      else if (q === 'JK') label = 'JK (Jammu & Kashmir Quota)';
      else if (q === 'LA') label = 'LA (Ladakh Quota)';
      list.push({ value: q, label });
    });
    return list;
  }, [filterOptions]);

  // Academic Year options (guaranteeing 2026 & 2025)
  const yearOptions = useMemo(() => {
    const yearSet = new Set<number>([2026, 2025]);
    if (filterOptions?.years) {
      filterOptions.years.forEach((y) => yearSet.add(y));
    }
    return Array.from(yearSet)
      .sort((a, b) => b - a)
      .map((y) => ({
        value: String(y),
        label: `${y} Cutoffs`,
      }));
  }, [filterOptions]);

  // Query cutoffs
  const queryParams = useMemo(() => ({
    round_no: selectedRounds.length > 0 ? selectedRounds.join(',') : undefined,
    institute_type: instituteType || undefined,
    institute_name: selectedInstitutes.length > 0 ? selectedInstitutes.join('||') : undefined,
    candidate_state: selectedStates.length > 0 ? selectedStates.join(',') : undefined,
    academic_program: selectedPrograms.length > 0 ? selectedPrograms.join('||') : undefined,
    category: category || undefined,
    quota: quota || undefined,
    gender: gender || undefined,
    academic_year: academicYear ? Number(academicYear) : undefined,
    max_rank: candidateRank ? Number(candidateRank) : undefined,
    page,
    page_size: pageSize,
    sort_by: sortBy,
  }), [selectedRounds, instituteType, selectedInstitutes, selectedStates, selectedPrograms, category, quota, gender, academicYear, candidateRank, page, pageSize, sortBy]);

  const { data: cutoffsData, isLoading: isCutoffsLoading, isError, error, refetch } = useQuery({
    queryKey: ['josaaCutoffs', queryParams],
    queryFn: () => getJosaaCutoffs(queryParams),
    enabled: hasSearched,
  });

  // Handle Search Submission
  const handleSearch = () => {
    setPage(1);
    setHasSearched(true);

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
    if (candidateRank) params.set('rank', candidateRank);

    setSearchParams(params);
  };

  // Reset Filters
  const handleReset = () => {
    setSelectedRounds([]);
    setInstituteType('');
    setSelectedInstitutes([]);
    setSelectedStates([]);
    setSelectedPrograms([]);
    setCategory('');
    setQuota('');
    setGender('');
    setCandidateRank('');
    setHasSearched(true);
    setPage(1);
    setSearchParams(new URLSearchParams());
    toast.success('Filters reset');
  };

  // Active filter chips (each selected institute, state, and program has its own individual removable chip)
  const activeFilterChips: ActiveFilter[] = useMemo(() => {
    const chips: ActiveFilter[] = [];
    selectedRounds.forEach((r) => {
      chips.push({ id: `round:${r}`, label: 'Round', value: `Round ${r}` });
    });
    if (instituteType) chips.push({ id: 'type', label: 'Type', value: instituteType });
    
    selectedInstitutes.forEach((inst) => {
      chips.push({
        id: `institute:${inst}`,
        label: 'Institute',
        value: inst,
      });
    });

    selectedStates.forEach((st) => {
      chips.push({
        id: `state:${st}`,
        label: 'Candidate State',
        value: st,
      });
    });

    selectedPrograms.forEach((prog) => {
      chips.push({
        id: `program:${prog}`,
        label: 'Program',
        value: prog,
      });
    });

    if (category) chips.push({ id: 'category', label: 'Category', value: category });
    if (quota) chips.push({ id: 'quota', label: 'Quota', value: quota });
    if (gender) chips.push({ id: 'gender', label: 'Pool', value: gender });
    if (candidateRank) chips.push({ id: 'rank', label: 'JEE Rank ≤', value: `#${candidateRank}` });
    return chips;
  }, [selectedRounds, instituteType, selectedInstitutes, selectedStates, selectedPrograms, category, quota, gender, candidateRank]);

  const removeFilterChip = (id: string) => {
    if (id.startsWith('round:')) {
      const val = id.substring('round:'.length);
      setSelectedRounds((prev) => prev.filter((item) => item !== val));
      return;
    }
    if (id === 'round') setSelectedRounds([]);
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
    if (id === 'rank') setCandidateRank('');
  };

  // Institute Type styling helper
  const getInstituteTypeBadge = (type: string) => {
    switch ((type || '').toUpperCase()) {
      case 'IIT':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">IIT</span>;
      case 'NIT':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-blue-100 text-blue-900 border border-blue-300">NIT</span>;
      case 'IIIT':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-purple-100 text-purple-900 border border-purple-300">IIIT</span>;
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-slate-100 text-slate-800 border border-slate-300">GFTI</span>;
    }
  };

  // Quota description tooltip and badge helper
  const getQuotaBadge = (quotaCode: string) => {
    const q = (quotaCode || '').toUpperCase();
    let title = q;
    let colorClass = 'bg-slate-50 text-slate-800 border-slate-200';

    if (q === 'AI') {
      title = 'All India Quota (Open to candidates across India)';
      colorClass = 'bg-blue-50 text-blue-800 border-blue-200';
    } else if (q === 'HS') {
      title = 'Home State Quota (Reserved for state domicile candidates)';
      colorClass = 'bg-emerald-50 text-emerald-800 border-emerald-200';
    } else if (q === 'OS') {
      title = 'Other State Quota (NIT candidates outside home state)';
      colorClass = 'bg-amber-50 text-amber-800 border-amber-200';
    } else if (q === 'GO') {
      title = 'Goa State Quota (Reserved specifically for candidates from Goa at NIT Goa)';
      colorClass = 'bg-purple-50 text-purple-800 border-purple-200';
    } else if (q === 'JK') {
      title = 'Jammu & Kashmir Quota';
      colorClass = 'bg-cyan-50 text-cyan-800 border-cyan-200';
    } else if (q === 'LA') {
      title = 'Ladakh Quota';
      colorClass = 'bg-teal-50 text-teal-800 border-teal-200';
    }

    return (
      <span
        className={`font-semibold text-xs border px-2 py-0.5 rounded cursor-help ${colorClass}`}
        title={title}
      >
        {q}
      </span>
    );
  };

  const candidateRankNum = candidateRank ? parseInt(candidateRank, 10) : null;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border border-slate-800 rounded-xl p-6 text-white shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-lg border border-indigo-500/30">
                <Award className="w-6 h-6" />
              </div>
              <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white">
                JoSAA Admissions Cutoff Explorer
              </h1>
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Standalone JoSAA DB
              </span>
            </div>
            <p className="text-xs md:text-sm text-slate-300 max-w-2xl pl-1">
              Search official JoSAA opening and closing ranks for IITs, NITs, IIITs, and Other-GFTIs. Filter by CAP Round, Institute Type, Program, Category, and Rank.
            </p>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <div className="bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-2 text-right">
              <div className="text-[11px] text-slate-400 font-medium">Database Status</div>
              <div className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5 justify-end">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                {filterOptions?.institutes?.length || 0} Institutes • {filterOptions?.rounds?.length || 0} Rounds
              </div>
            </div>

            {/* Live Scraper Progress Pill */}
            {scraperStatus?.is_running && (
              <button
                onClick={() => setShowScraperModal(true)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-indigo-500/20 border border-indigo-500/40 text-xs font-semibold text-indigo-300 hover:bg-indigo-500/30 transition-all animate-pulse"
                title="Click to view live scraping progress"
              >
                <Spinner className="w-3.5 h-3.5" />
                <span>Scraping 2025 & 2026 ({scraperStatus.progress_percent}%)</span>
              </button>
            )}

            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                if (scraperStatus?.is_running) {
                  setShowScraperModal(true);
                } else {
                  scraperMutation.mutate();
                }
              }}
              disabled={scraperMutation.isPending}
              className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-semibold shadow-sm shadow-indigo-900/30"
              title="Scrape complete official cutoffs for Years 2025 & 2026 across all rounds"
            >
              <Globe className={`w-3.5 h-3.5 mr-1.5 ${scraperStatus?.is_running ? 'animate-spin' : ''}`} />
              {scraperStatus?.is_running ? 'View Scraper Progress' : 'Web Scrape JoSAA (2025 & 2026)'}
            </Button>

            <Button
              variant="danger"
              size="sm"
              onClick={() => setShowWipeModal(true)}
              className="text-xs bg-red-600/90 hover:bg-red-700 text-white"
              title="Wipe all JoSAA records"
            >
              <Trash2 className="w-3.5 h-3.5 mr-1.5" />
              Wipe JoSAA DB
            </Button>
          </div>
        </div>
      </div>

      {/* JoSAA Scraping Progress Modal */}
      {showScraperModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl max-w-xl w-full p-6 space-y-5 text-white">
            {/* Header */}
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center flex-shrink-0 text-indigo-400">
                  <Globe className={`w-5 h-5 ${scraperStatus?.is_running ? 'animate-spin' : ''}`} />
                </div>
                <div>
                  <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                    JoSAA Multi-Year Web Scraper
                    {scraperStatus?.is_running && (
                      <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 animate-pulse">
                        Live Scraping
                      </span>
                    )}
                    {scraperStatus?.status === 'COMPLETED' && (
                      <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                        Completed
                      </span>
                    )}
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Extracting complete Opening & Closing Ranks across all 5 rounds for 2025 & 2026.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowScraperModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Progress Bar Component */}
            <div className="space-y-2 bg-slate-950/70 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-300 flex items-center gap-2">
                  {scraperStatus?.is_running && <Spinner className="w-3.5 h-3.5" />}
                  {scraperStatus?.current_year ? `Year ${scraperStatus.current_year} • Round ${scraperStatus.current_round} of 5` : 'Scraping Progress'}
                </span>
                <span className="font-mono font-bold text-indigo-400 text-sm">
                  {scraperStatus?.progress_percent ?? 0}%
                </span>
              </div>

              {/* Outer Bar */}
              <div className="w-full bg-slate-800 h-3.5 rounded-full overflow-hidden p-0.5 border border-slate-700/60">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    scraperStatus?.status === 'COMPLETED'
                      ? 'bg-gradient-to-r from-emerald-500 to-teal-400'
                      : scraperStatus?.status === 'FAILED'
                      ? 'bg-red-500'
                      : 'bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-400'
                  }`}
                  style={{ width: `${Math.min(100, Math.max(2, scraperStatus?.progress_percent ?? 0))}%` }}
                />
              </div>

              {/* Current status message */}
              <p className="text-xs text-slate-400 pt-1 flex items-center gap-1.5">
                <span className="text-indigo-400 font-medium">Activity:</span>
                <span>{scraperStatus?.message || 'Connecting to official portals...'}</span>
              </p>
            </div>

            {/* Real-time Metric Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3 text-center">
                <div className="text-[11px] text-slate-400 font-medium">Completed Rounds</div>
                <div className="text-base font-bold text-slate-100 mt-0.5">
                  {scraperStatus?.completed_rounds ?? 0} / 10
                </div>
              </div>

              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3 text-center">
                <div className="text-[11px] text-slate-400 font-medium">Year 2025 Records</div>
                <div className="text-base font-bold text-indigo-300 mt-0.5">
                  {scraperStatus?.records_2025?.toLocaleString() ?? 0}
                </div>
              </div>

              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3 text-center">
                <div className="text-[11px] text-slate-400 font-medium">Year 2026 Records</div>
                <div className="text-base font-bold text-purple-300 mt-0.5">
                  {scraperStatus?.records_2026?.toLocaleString() ?? 0}
                </div>
              </div>

              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3 text-center">
                <div className="text-[11px] text-slate-400 font-medium">Total Cutoffs</div>
                <div className="text-base font-bold text-emerald-400 mt-0.5">
                  {scraperStatus?.total_records?.toLocaleString() ?? 0}
                </div>
              </div>
            </div>

            {/* Completion or Error Banners */}
            {scraperStatus?.status === 'COMPLETED' && (
              <div className="bg-emerald-950/40 border border-emerald-500/40 rounded-xl p-3 text-xs text-emerald-300 flex items-center gap-2.5">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                <div>
                  <p className="font-semibold text-emerald-200">Scraping Completed Successfully!</p>
                  <p className="text-emerald-300/80">Both 2025 and 2026 cutoffs are ingested, deduplicated, and ready for exploration.</p>
                </div>
              </div>
            )}

            {scraperStatus?.status === 'FAILED' && (
              <div className="bg-red-950/40 border border-red-500/40 rounded-xl p-3 text-xs text-red-300 flex items-center gap-2.5">
                <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
                <div>
                  <p className="font-semibold text-red-200">Scraper encountered an error:</p>
                  <p className="text-red-300/80">{scraperStatus?.error || 'Network timeout or connection error.'}</p>
                </div>
              </div>
            )}

            {/* Action Footer */}
            <div className="flex items-center justify-between pt-2 border-t border-slate-800">
              <div className="text-[11px] text-slate-400">
                {scraperStatus?.is_running ? 'You can safely close this modal; scraping continues in the background.' : 'Ready to search and filter.'}
              </div>
              <div className="flex items-center gap-2">
                {scraperStatus?.status === 'COMPLETED' && (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => {
                      setShowScraperModal(false);
                      queryClient.invalidateQueries({ queryKey: ['josaaFilterOptions'] });
                      queryClient.invalidateQueries({ queryKey: ['josaaCutoffs'] });
                    }}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs"
                  >
                    Explore Cutoffs Now
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowScraperModal(false)}
                  className="text-xs text-slate-300 border-slate-700 hover:bg-slate-800"
                >
                  {scraperStatus?.is_running ? 'Run in Background' : 'Close'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Wipe Confirmation Modal */}
      {showWipeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 space-y-4 border border-red-100">
            <div className="flex items-center gap-3 text-red-600">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 className="font-bold text-gray-900 text-base">Wipe JoSAA Database Records?</h3>
                <p className="text-xs text-red-600 font-medium">This will clear all JoSAA cutoff records and institutes.</p>
              </div>
            </div>
            <div className="text-xs text-gray-600 bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-1">
              <p className="font-semibold text-amber-900">Important Notes:</p>
              <p>1. Only the independent <span className="font-mono">josaa.db</span> file will be cleared.</p>
              <p>2. Your MHT-CET database and admin account remain completely unaffected.</p>
              <p>3. You can click "Web Scrape JoSAA" anytime to scrape and reload official cutoffs for Years 2025 and 2026.</p>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowWipeModal(false)}
                disabled={wipeMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => wipeMutation.mutate()}
                isLoading={wipeMutation.isPending}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                Yes, Wipe JoSAA DB
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Inline Scraping Progress Banner (Always visible while scraping is active) */}
      {scraperStatus?.is_running && (
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border border-indigo-500/40 rounded-xl p-4 shadow-lg text-white space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 flex-shrink-0">
                <Globe className="w-5 h-5 animate-spin" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-slate-100">Live Official Web Scraping Active</span>
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 animate-pulse">
                    {scraperStatus.current_year ? `Year ${scraperStatus.current_year} • Round ${scraperStatus.current_round} of 5` : 'Processing'}
                  </span>
                </div>
                <p className="text-xs text-slate-300 mt-0.5">
                  {scraperStatus.message || 'Connecting to official portals...'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 self-end sm:self-center">
              <div className="text-right">
                <span className="font-mono font-bold text-indigo-400 text-base">
                  {scraperStatus.progress_percent}%
                </span>
                <div className="text-[10px] text-slate-400">
                  {scraperStatus.completed_rounds} / 10 rounds completed
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowScraperModal(true)}
                className="text-xs border-indigo-500/40 text-indigo-300 hover:bg-indigo-950/60"
              >
                View Details
              </Button>
            </div>
          </div>

          {/* Progress Bar Track */}
          <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden p-0.5 border border-slate-700/60">
            <div
              className="h-full rounded-full transition-all duration-500 bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-400"
              style={{ width: `${Math.max(3, scraperStatus.progress_percent)}%` }}
            />
          </div>

          <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-400 pt-0.5">
            <span>Year 2025 Scraped: <strong className="text-indigo-300 font-semibold">{scraperStatus.records_2025.toLocaleString()}</strong> cutoffs</span>
            <span>Year 2026 Scraped: <strong className="text-purple-300 font-semibold">{scraperStatus.records_2026.toLocaleString()}</strong> cutoffs</span>
            <span>Total Ingested: <strong className="text-emerald-400 font-semibold">{scraperStatus.total_records.toLocaleString()}</strong> cutoffs</span>
          </div>
        </div>
      )}

      {/* Empty Database Callout Banner */}
      {!scraperStatus?.is_running && (!filterOptions?.institutes || filterOptions.institutes.length === 0) && (
        <div className="bg-amber-950/30 border border-amber-500/40 rounded-xl p-5 text-amber-200 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-amber-500/20 border border-amber-500/30 flex items-center justify-center flex-shrink-0 text-amber-400">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h4 className="font-bold text-sm text-amber-100">JoSAA Database is Empty</h4>
              <p className="text-xs text-amber-300/80 mt-0.5">
                No cutoff records found. Run the official web scraper to scrape and populate cutoffs for both 2025 and 2026 with live progress tracking.
              </p>
            </div>
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={() => scraperMutation.mutate()}
            disabled={scraperMutation.isPending}
            className="bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs whitespace-nowrap shadow-sm"
          >
            <Globe className="w-3.5 h-3.5 mr-1.5" />
            Start Web Scraper (2025 & 2026)
          </Button>
        </div>
      )}

      {/* Multi-Panel Switcher Navigation */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 shadow-md">
        <div className="flex flex-col md:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2 bg-slate-950/90 p-1.5 rounded-lg border border-slate-800 w-full md:w-auto">
            <Link
              to="/search?panel=state"
              className="flex-1 md:flex-initial flex items-center justify-center gap-2 px-5 py-2.5 rounded-md text-xs font-bold text-slate-400 hover:text-white hover:bg-slate-800/80 transition-all"
            >
              <Building2 className="w-4 h-4 text-primary-400" />
              <span>MHT-CET (Maharashtra State)</span>
            </Link>

            <Link
              to="/search?panel=all_india"
              className="flex-1 md:flex-initial flex items-center justify-center gap-2 px-5 py-2.5 rounded-md text-xs font-bold text-slate-400 hover:text-white hover:bg-slate-800/80 transition-all"
            >
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <span>MHT-CET (All India Cutoff)</span>
            </Link>

            <div className="flex-1 md:flex-initial flex items-center justify-center gap-2 px-5 py-2.5 rounded-md text-xs font-bold bg-amber-500/20 text-amber-300 shadow-sm ring-1 ring-amber-500/50">
              <Award className="w-4 h-4 text-amber-400" />
              <span>JoSAA (IIT / NIT / IIIT)</span>
              <span className="ml-1 text-[10px] bg-amber-500/30 text-amber-200 px-2 py-0.5 rounded-full border border-amber-400/40">
                Active Panel
              </span>
            </div>
          </div>

          <div className="text-right px-2 hidden lg:block">
            <span className="text-xs font-bold text-slate-200">
              🎓 National Institutes Cutoff Database
            </span>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Opening & Closing ranks for Joint Seat Allocation Authority
            </p>
          </div>
        </div>
      </div>

      {/* Filter Section */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-4 bg-slate-50/70 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-slate-600" />
            <span className="text-sm font-semibold text-slate-800">Counselling Search Filters</span>
          </div>
          <div className="text-xs text-slate-500">
            All JoSAA cutoffs are reported as exact ranks (Opening & Closing)
          </div>
        </div>

        <div className="p-5 space-y-4">
          {/* Row 1: CAP Round, Institute Type, Category, Quota */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <SearchableSelect
              label="JoSAA Round"
              placeholder="All JoSAA Rounds"
              multiple={true}
              values={selectedRounds}
              onMultiChange={setSelectedRounds}
              options={roundSelectOptions}
              helperText={
                selectedRounds.length > 0
                  ? `${selectedRounds.length} round(s) selected`
                  : 'Multi-select any combination of JoSAA rounds'
              }
            />

            <Select
              label="Institute Type"
              value={instituteType}
              onChange={(e) => {
                setInstituteType(e.target.value);
                // Clear selected institute if type changed and institute no longer belongs
                setSelectedInstitutes([]);
              }}
              options={instituteTypeOptions}
            />

            <Select
              label="Category"
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

          {/* Row 2: Institute Name, Academic Program */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <SearchableSelect
              label="Institute Name (IIT / NIT / IIIT / GFTI)"
              placeholder={instituteType ? `Select ${instituteType}s...` : "Select or search institutes..."}
              options={instituteOptions}
              multiple
              values={selectedInstitutes}
              onMultiChange={setSelectedInstitutes}
              helperText={selectedInstitutes.length ? `${selectedInstitutes.length} institute(s) selected` : undefined}
            />

            <SearchableSelect
              label="Academic Program / Branch"
              placeholder="Select or search engineering programs..."
              options={programOptions}
              multiple
              values={selectedPrograms}
              onMultiChange={setSelectedPrograms}
              helperText={selectedPrograms.length ? `${selectedPrograms.length} program(s) selected` : undefined}
            />
          </div>

          {/* Row 3: Home State (HS Quota), Seat Pool / Gender, Candidate JEE Rank, Year */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-1">
            <SearchableSelect
              label="Candidate Home State"
              placeholder={stateOptions.length ? "All States (No Quota Restriction)..." : "No states available"}
              options={stateOptions}
              multiple
              values={selectedStates}
              onMultiChange={setSelectedStates}
              helperText={
                selectedStates.length
                  ? `${selectedStates.length} state(s) selected • HS for local, OS for other states`
                  : 'Applies HS quota for local NIT and OS quota for other states across India'
              }
            />

            <Select
              label="Seat Pool / Gender"
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              options={[
                { value: '', label: 'All Seat Pools (Open & Female-only)' },
                { value: 'Gender-Neutral', label: 'Gender-Neutral' },
                { value: 'Female-only', label: 'Female-only (including Supernumerary)' },
              ]}
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Candidate JEE Rank <span className="text-xs text-gray-400 font-normal">(Optional Eligibility Filter)</span>
              </label>
              <div className="relative">
                <input
                  type="number"
                  min="1"
                  placeholder="e.g. 2500"
                  value={candidateRank}
                  onChange={(e) => setCandidateRank(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
                {candidateRank && (
                  <button
                    type="button"
                    onClick={() => setCandidateRank('')}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs"
                  >
                    Clear
                  </button>
                )}
              </div>
              <p className="mt-1 text-[11px] text-gray-500">
                Filters to programs where your rank ≤ Closing Rank (eligible)
              </p>
            </div>

            <Select
              label="Academic Year"
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
              options={yearOptions}
            />
          </div>

          {/* Active Filter Chips */}
          <FilterChips
            filters={activeFilterChips}
            onRemove={removeFilterChip}
            onClearAll={handleReset}
          />

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
            <div className="text-xs text-slate-500">
              {hasSearched && cutoffsData && (
                <span>Found <strong className="text-slate-800">{cutoffsData.total}</strong> matching cutoff allotment records</span>
              )}
            </div>

            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="md"
                onClick={handleReset}
                className="text-slate-700 hover:bg-slate-100"
              >
                <RotateCcw className="w-4 h-4 mr-1.5" />
                Reset Filters
              </Button>

              <Button
                variant="primary"
                size="md"
                onClick={handleSearch}
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold shadow-sm"
              >
                <Search className="w-4 h-4 mr-1.5" />
                Find JoSAA Cutoffs
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Results Section */}
      {hasSearched ? (
        <div className="space-y-4">
          {/* Results Toolbar */}
          <div className="bg-white p-3 rounded-lg border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-xs">
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-slate-800">
                {cutoffsData?.total ?? 0} Cutoff Records
              </span>

              {candidateRankNum !== null && (
                <span className="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded font-medium">
                  Showing programs where Rank ≤ #{candidateRankNum}
                </span>
              )}
            </div>

            <div className="flex items-center gap-3">
              {/* Sort by */}
              <div className="flex items-center gap-1.5">
                <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="text-xs bg-slate-50 border border-slate-300 rounded px-2 py-1 text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="rank_asc">Sort: Closing Rank (Ascending)</option>
                  <option value="rank_desc">Sort: Closing Rank (Descending)</option>
                  <option value="opening_rank_asc">Sort: Opening Rank (Ascending)</option>
                  <option value="institute">Sort: Institute Name</option>
                  <option value="program">Sort: Program Name</option>
                </select>
              </div>

              {/* View toggle */}
              <div className="flex items-center border border-slate-200 rounded-md overflow-hidden">
                <button
                  type="button"
                  onClick={() => setViewMode('table')}
                  className={`p-1.5 text-xs font-medium ${
                    viewMode === 'table' ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'text-slate-600 hover:bg-slate-50'
                  }`}
                  title="Table View"
                >
                  <TableIcon className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('cards')}
                  className={`p-1.5 text-xs font-medium ${
                    viewMode === 'cards' ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'text-slate-600 hover:bg-slate-50'
                  }`}
                  title="Cards View"
                >
                  <LayoutGrid className="w-4 h-4" />
                </button>
              </div>

              {/* Export to CSV */}
              <a
                href={getJosaaExportUrl(queryParams)}
                download="josaa_cutoffs.csv"
                className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-md transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                Export CSV
              </a>
            </div>
          </div>

          {/* Loading Indicator */}
          {isCutoffsLoading ? (
            <div className="bg-white rounded-xl p-12 border border-slate-200 flex flex-col items-center justify-center space-y-3">
              <Spinner className="w-8 h-8 text-indigo-600" />
              <p className="text-sm font-medium text-slate-600">Querying JoSAA database...</p>
            </div>
          ) : isError ? (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center text-red-800">
              <p className="font-semibold text-sm">Failed to load JoSAA cutoffs</p>
              <p className="text-xs text-red-600 mt-1">{String((error as any)?.message || 'Internal error')}</p>
              <Button size="sm" variant="outline" onClick={() => refetch()} className="mt-3">
                Try Again
              </Button>
            </div>
          ) : cutoffsData?.items.length === 0 ? (
            <div className="bg-white rounded-xl p-12 border border-slate-200 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
                <Search className="w-6 h-6" />
              </div>
              <h3 className="text-base font-semibold text-slate-800">No JoSAA cutoffs found matching criteria</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Try widening your search filters, selecting "All Institute Types", or checking your Category and Rank filter.
              </p>
              <Button size="sm" variant="outline" onClick={handleReset} className="mt-2">
                Reset All Filters
              </Button>
            </div>
          ) : viewMode === 'table' ? (
            /* Table View */
            <div className="bg-white rounded-xl shadow-xs border border-slate-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold uppercase tracking-wider text-[11px]">
                      <th className="py-3 px-4">Institute</th>
                      <th className="py-3 px-4">Program & Degree</th>
                      <th className="py-3 px-3 text-center">Round</th>
                      <th className="py-3 px-3 text-center">Quota</th>
                      <th className="py-3 px-3">Seat Pool</th>
                      <th className="py-3 px-3 text-center">Category</th>
                      <th className="py-3 px-4 text-right bg-emerald-50/50 text-emerald-900 border-l border-emerald-100">
                        Opening Rank (OR)
                      </th>
                      <th className="py-3 px-4 text-right bg-blue-50/50 text-blue-900 border-l border-blue-100">
                        Closing Rank (CR)
                      </th>
                      {candidateRankNum !== null && (
                        <th className="py-3 px-3 text-center bg-indigo-50/50 text-indigo-900 border-l border-indigo-100">
                          Eligibility
                        </th>
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {cutoffsData?.items.map((row: JosaaCutoff) => {
                      const isEligible = candidateRankNum !== null ? candidateRankNum <= row.closing_rank : null;
                      const isHighlyCompetitive = candidateRankNum !== null ? candidateRankNum <= row.opening_rank : null;

                      return (
                        <tr key={row.id} className="hover:bg-slate-50/80 transition-colors">
                          {/* Institute */}
                          <td className="py-3 px-4">
                            <div className="font-semibold text-slate-900 text-xs flex items-center gap-2">
                              {row.institute_name}
                            </div>
                            <div className="flex items-center gap-1.5 mt-1">
                              {getInstituteTypeBadge(row.institute_type)}
                              {row.institute_state && (
                                <span className="text-[10px] text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                                  {row.institute_state}
                                </span>
                              )}
                              {row.institute_code && (
                                <span className="text-[10px] text-slate-400 font-mono">
                                  ({row.institute_code})
                                </span>
                              )}
                            </div>
                          </td>

                          {/* Program */}
                          <td className="py-3 px-4 max-w-xs">
                            <div className="font-medium text-slate-800 text-xs leading-snug">
                              {row.program_name}
                            </div>
                            <div className="mt-1">
                              <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-medium">
                                {row.degree_type || 'B.Tech / B.E.'}
                              </span>
                            </div>
                          </td>

                          {/* Round */}
                          <td className="py-3 px-3 text-center whitespace-nowrap">
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
                              Round {row.round_no}
                            </span>
                          </td>

                          {/* Quota */}
                          <td className="py-3 px-3 text-center whitespace-nowrap">
                            {getQuotaBadge(row.quota)}
                          </td>

                          {/* Gender */}
                          <td className="py-3 px-3 whitespace-nowrap">
                            {row.gender.includes('Female') ? (
                              <span className="text-[11px] text-pink-700 bg-pink-50 border border-pink-200 px-2 py-0.5 rounded-full font-medium">
                                Female-only
                              </span>
                            ) : (
                              <span className="text-[11px] text-slate-600 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded-full font-medium">
                                Gender-Neutral
                              </span>
                            )}
                          </td>

                          {/* Category */}
                          <td className="py-3 px-3 text-center whitespace-nowrap">
                            <span className="inline-flex items-center px-2 py-0.5 rounded font-bold text-xs bg-indigo-50 text-indigo-800 border border-indigo-200">
                              {row.category_code}
                            </span>
                          </td>

                          {/* Opening Rank */}
                          <td className="py-3 px-4 text-right whitespace-nowrap bg-emerald-50/20 border-l border-emerald-100">
                            <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded">
                              #{row.opening_rank.toLocaleString()}
                            </span>
                          </td>

                          {/* Closing Rank */}
                          <td className="py-3 px-4 text-right whitespace-nowrap bg-blue-50/20 border-l border-blue-100">
                            <span className="text-xs font-extrabold text-blue-700 bg-blue-50 border border-blue-200 px-2.5 py-1 rounded shadow-2xs">
                              #{row.closing_rank.toLocaleString()}
                            </span>
                          </td>

                          {/* Eligibility */}
                          {candidateRankNum !== null && (
                            <td className="py-3 px-3 text-center whitespace-nowrap bg-indigo-50/20 border-l border-indigo-100">
                              {isHighlyCompetitive ? (
                                <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                                  <CheckCircle2 className="w-3 h-3" /> Safe
                                </span>
                              ) : isEligible ? (
                                <span className="inline-flex items-center gap-1 text-[11px] font-bold text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full">
                                  In Reach
                                </span>
                              ) : (
                                <span className="text-[11px] font-medium text-slate-400">
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
            /* Cards View */
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {cutoffsData?.items.map((row: JosaaCutoff) => {
                const isEligible = candidateRankNum !== null ? candidateRankNum <= row.closing_rank : null;

                return (
                  <div 
                    key={row.id} 
                    className="bg-white rounded-xl border border-slate-200 p-4 shadow-2xs hover:shadow-md transition-shadow flex flex-col justify-between"
                  >
                    <div>
                      {/* Card Header */}
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {getInstituteTypeBadge(row.institute_type)}
                          <span className="text-[11px] font-semibold bg-slate-100 text-slate-700 px-2 py-0.5 rounded-full">
                            Round {row.round_no}
                          </span>
                          <span className="text-[11px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-0.5 rounded">
                            {row.category_code}
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-400 font-medium">
                          {row.academic_year}
                        </span>
                      </div>

                      {/* Institute Name */}
                      <h4 className="font-bold text-slate-900 text-sm leading-snug line-clamp-2">
                        {row.institute_name}
                      </h4>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        {row.institute_state || 'India'}
                      </p>

                      {/* Program */}
                      <div className="mt-3 p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                        <div className="text-xs font-semibold text-slate-800 line-clamp-2">
                          {row.program_name}
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-500 mt-1">
                          <span>{row.degree_type || 'B.Tech'}</span>
                          <span className="flex items-center gap-1">Quota: {getQuotaBadge(row.quota)}</span>
                        </div>
                      </div>
                    </div>

                    {/* Ranks Display Box */}
                    <div className="mt-4 pt-3 border-t border-slate-100">
                      <div className="grid grid-cols-2 gap-2 text-center">
                        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-2">
                          <div className="text-[10px] uppercase font-bold text-emerald-800 tracking-wider">
                            Opening Rank
                          </div>
                          <div className="text-sm font-extrabold text-emerald-700 mt-0.5">
                            #{row.opening_rank.toLocaleString()}
                          </div>
                        </div>

                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-2">
                          <div className="text-[10px] uppercase font-bold text-blue-800 tracking-wider">
                            Closing Rank
                          </div>
                          <div className="text-sm font-extrabold text-blue-700 mt-0.5">
                            #{row.closing_rank.toLocaleString()}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between mt-2.5 text-[11px] text-slate-500 px-1">
                        <span>Pool: <strong className="text-slate-700">{row.gender.includes('Female') ? 'Female-only' : 'Gender-Neutral'}</strong></span>
                        {candidateRankNum !== null && (
                          isEligible ? (
                            <span className="font-bold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">Eligible</span>
                          ) : (
                            <span className="font-medium text-slate-400">Closed</span>
                          )
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Pagination Controls */}
          {cutoffsData && cutoffsData.total_pages > 1 && (
            <div className="bg-white p-3 rounded-lg border border-slate-200 flex items-center justify-between shadow-2xs">
              <div className="text-xs text-slate-500">
                Page {cutoffsData.page} of {cutoffsData.total_pages} ({cutoffsData.total} total cutoffs)
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <span className="text-xs font-semibold px-2 text-slate-700">
                  {page} / {cutoffsData.total_pages}
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page >= cutoffsData.total_pages}
                  onClick={() => setPage((p) => Math.min(cutoffsData.total_pages, p + 1))}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Initial Ready State */
        <div className="bg-white rounded-xl p-10 border border-slate-200 text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center mx-auto text-indigo-600">
            <Award className="w-7 h-7" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-900">
              Ready to Explore JoSAA Cutoffs
            </h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Select your filters above (such as CAP Round, Institute Type, Institute Name, Academic Program, or Category) and click <strong>"Find JoSAA Cutoffs"</strong> to view official opening and closing ranks.
            </p>
          </div>
          <div className="flex justify-center pt-2">
            <Button
              variant="primary"
              size="md"
              onClick={handleSearch}
              className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold"
            >
              <Search className="w-4 h-4 mr-1.5" />
              Search All JoSAA Cutoffs
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default JosaaSearchPage;
