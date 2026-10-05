import React, { useState, useMemo, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Building2, BookOpen, Download, LayoutGrid, Table as TableIcon,
  CheckCircle2, SlidersHorizontal, ExternalLink, ArrowUpDown, Filter, Sparkles,
  Trash2, RefreshCw, AlertTriangle, Globe, School, Info, TrendingUp, Layers, Check,
  Landmark, Award, Calendar, RotateCcw
} from 'lucide-react';
import toast from 'react-hot-toast';

import { 
  getBitsFilterOptions, 
  getBitsCutoffs, 
  getBitsStats,
  getBitsExportUrl,
  scrapeBitsData,
  getBitsScraperStatus,
  resetBitsDatabase,
  BitsCutoffItem,
  BitsScraperStatus
} from '../api/bits';
import SearchableSelect, { SearchableOption } from '../components/ui/SearchableSelect';
import Select from '../components/ui/Select';
import Button from '../components/ui/Button';
import FilterChips, { ActiveFilter } from '../components/ui/FilterChips';
import Badge from '../components/ui/Badge';
import Spinner from '../components/ui/Spinner';
import Modal from '../components/ui/Modal';
import Pagination from '../components/ui/Pagination';
import { formatNumber } from '../utils/formatters';

export const BitsSearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

  const [showWipeModal, setShowWipeModal] = useState(false);
  const [showScraperModal, setShowScraperModal] = useState(false);
  const [pollScraper, setPollScraper] = useState(false);
  const [viewMode, setViewMode] = useState<'table' | 'cards' | 'comparison'>('table');

  // URL state query parameters
  const yearParam = searchParams.get('year') || '2026-2027'; // Default to latest year
  const campusParam = searchParams.get('campus') || '';
  const programParam = searchParams.get('program') || '';
  const degreeParam = searchParams.get('degree') || '';
  const scoreParam = searchParams.get('student_score') || '';
  const sortParam = searchParams.get('sort_by') || 'score_desc';
  const pageParam = parseInt(searchParams.get('page') || '1', 10);
  const pageSizeParam = parseInt(searchParams.get('page_size') || '50', 10);

  // Multi-select parsed arrays
  const selectedCampuses = useMemo(
    () => (campusParam ? campusParam.split('||').map((c) => c.trim()).filter(Boolean) : []),
    [campusParam]
  );
  const selectedPrograms = useMemo(
    () => (programParam ? programParam.split('||').map((p) => p.trim()).filter(Boolean) : []),
    [programParam]
  );

  // Background Scraper Status Query with automatic 1-second polling while running
  const { data: scraperStatus } = useQuery<BitsScraperStatus>({
    queryKey: ['bitsScraperStatus'],
    queryFn: getBitsScraperStatus,
    refetchInterval: (query) => {
      const data = query.state.data;
      return (data?.is_running || pollScraper) ? 1000 : false;
    },
  });

  // Watch scraper status completion
  const prevRunningRef = useRef(false);
  useEffect(() => {
    if (scraperStatus) {
      if (prevRunningRef.current && !scraperStatus.is_running) {
        setPollScraper(false);
        if (scraperStatus.status === 'COMPLETED') {
          toast.success(scraperStatus.message || 'BITSAT cutoffs scraped successfully!');
          queryClient.invalidateQueries({ queryKey: ['bitsFilterOptions'] });
          queryClient.invalidateQueries({ queryKey: ['bitsCutoffs'] });
          queryClient.invalidateQueries({ queryKey: ['bitsStats'] });
        } else if (scraperStatus.status === 'FAILED') {
          toast.error(`BITSAT scraping failed: ${scraperStatus.error || 'Check server connection'}`);
        }
      }
      prevRunningRef.current = scraperStatus.is_running;
    }
  }, [scraperStatus, queryClient]);

  // Scraper Mutations
  const scraperMutation = useMutation({
    mutationFn: () => scrapeBitsData(['2026-2027', '2025-2026']),
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message || 'BITSAT scraper started!');
        setShowScraperModal(true);
        setPollScraper(true);
        queryClient.invalidateQueries({ queryKey: ['bitsScraperStatus'] });
      } else {
        toast.error(data.message);
      }
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.message || 'Failed to start BITSAT scraper');
    }
  });

  const wipeMutation = useMutation({
    mutationFn: resetBitsDatabase,
    onSuccess: (data) => {
      toast.success(data.message || 'BITS database reset successfully!');
      setShowWipeModal(false);
      queryClient.invalidateQueries({ queryKey: ['bitsFilterOptions'] });
      queryClient.invalidateQueries({ queryKey: ['bitsCutoffs'] });
      queryClient.invalidateQueries({ queryKey: ['bitsStats'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.message || 'Failed to reset BITS database');
    }
  });

  // Fetch Filter Options
  const { data: filterOptions, isLoading: isLoadingFilters } = useQuery({
    queryKey: ['bitsFilterOptions'],
    queryFn: getBitsFilterOptions,
    staleTime: 5 * 60 * 1000,
  });

  // Fetch Database Stats
  const { data: stats } = useQuery({
    queryKey: ['bitsStats'],
    queryFn: getBitsStats,
    staleTime: 60 * 1000,
  });

  // Cutoff Query Params
  const queryParams = useMemo(() => {
    return {
      academic_year: yearParam === 'ALL' ? undefined : (yearParam || undefined),
      campus_name: campusParam || undefined,
      program_name: programParam || undefined,
      degree_type: degreeParam || undefined,
      student_score: scoreParam ? parseInt(scoreParam, 10) : undefined,
      sort_by: sortParam,
      page: pageParam,
      page_size: pageSizeParam,
    };
  }, [yearParam, campusParam, programParam, degreeParam, scoreParam, sortParam, pageParam, pageSizeParam]);

  // Fetch Cutoffs
  const { data: cutoffsData, isLoading: isLoadingCutoffs, isFetching: isFetchingCutoffs } = useQuery({
    queryKey: ['bitsCutoffs', queryParams],
    queryFn: () => getBitsCutoffs(queryParams),
    staleTime: 30 * 1000,
  });

  // Helper to update URL search params
  const updateParam = (key: string, val: string | number | undefined | null) => {
    const next = new URLSearchParams(searchParams);
    if (val === undefined || val === null || val === '') {
      next.delete(key);
    } else {
      next.set(key, String(val));
    }
    // Reset page to 1 whenever filters change
    if (key !== 'page') {
      next.delete('page');
    }
    setSearchParams(next);
  };

  const handleClearAllFilters = () => {
    const next = new URLSearchParams();
    next.set('year', '2026-2027');
    if (pageSizeParam !== 50) {
      next.set('page_size', String(pageSizeParam));
    }
    setSearchParams(next);
  };

  // Build searchable options for UI
  const campusOptions: SearchableOption[] = useMemo(() => {
    if (!filterOptions?.campuses) return [];
    return filterOptions.campuses.map((c) => ({
      value: c.campus_name,
      label: c.campus_name,
      sublabel: c.location || c.state || undefined,
    }));
  }, [filterOptions]);

  const programOptions: SearchableOption[] = useMemo(() => {
    if (!filterOptions?.programs) return [];
    return filterOptions.programs.map((p) => ({
      value: p.program_name,
      label: p.program_name,
      sublabel: p.degree_type,
    }));
  }, [filterOptions]);

  // Active filter chips
  const activeFilters: ActiveFilter[] = useMemo(() => {
    const list: ActiveFilter[] = [];
    if (yearParam && yearParam !== 'ALL') {
      list.push({ id: 'year', label: 'Academic Year', value: yearParam });
    }
    if (selectedCampuses.length > 0) {
      if (selectedCampuses.length <= 2) {
        selectedCampuses.forEach((c) => {
          list.push({ id: `campus:${c}`, label: 'Campus', value: c });
        });
      } else {
        list.push({ id: 'campus', label: 'Campuses', value: `${selectedCampuses.length} Campuses Selected` });
      }
    }
    if (selectedPrograms.length > 0) {
      if (selectedPrograms.length <= 2) {
        selectedPrograms.forEach((p) => {
          list.push({ id: `program:${p}`, label: 'Program', value: p });
        });
      } else {
        list.push({ id: 'program', label: 'Programs', value: `${selectedPrograms.length} Programs Selected` });
      }
    }
    if (degreeParam) {
      list.push({ id: 'degree', label: 'Degree', value: degreeParam });
    }
    if (scoreParam) {
      list.push({ id: 'student_score', label: 'Your Score ≥', value: `${scoreParam} / 390` });
    }
    return list;
  }, [yearParam, selectedCampuses, selectedPrograms, degreeParam, scoreParam]);

  const handleRemoveFilter = (id: string) => {
    if (id === 'year') {
      updateParam('year', 'ALL');
    } else if (id.startsWith('campus:')) {
      const cVal = id.replace('campus:', '');
      const remaining = selectedCampuses.filter((c) => c !== cVal);
      updateParam('campus', remaining.join('||'));
    } else if (id.startsWith('program:')) {
      const pVal = id.replace('program:', '');
      const remaining = selectedPrograms.filter((p) => p !== pVal);
      updateParam('program', remaining.join('||'));
    } else {
      updateParam(id, '');
    }
  };

  // Year Comparison grouped view (2026-2027 vs 2025-2026)
  const comparisonGroups = useMemo(() => {
    if (!cutoffsData?.items || viewMode !== 'comparison') return [];
    const map = new Map<string, {
      campus: string;
      location?: string | null;
      program: string;
      degree: string;
      score_2026?: number;
      score_2025?: number;
    }>();

    cutoffsData.items.forEach((item) => {
      const key = `${item.campus_name}__${item.program_name}`;
      if (!map.has(key)) {
        map.set(key, {
          campus: item.campus_name,
          location: item.campus_location,
          program: item.program_name,
          degree: item.degree_type,
        });
      }
      const record = map.get(key)!;
      if (item.academic_year === '2026-2027') {
        record.score_2026 = item.cutoff_score;
      } else if (item.academic_year === '2025-2026') {
        record.score_2025 = item.cutoff_score;
      }
    });

    return Array.from(map.values());
  }, [cutoffsData?.items, viewMode]);

  return (
    <div className="min-h-screen bg-slate-50 p-4 sm:p-6 lg:p-8">
      {/* Header & Title Section */}
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-600 text-white shadow-md shadow-amber-500/20">
              <Landmark className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                  BITSAT Cutoff Explorer
                </h1>
                <Badge variant="warning" className="font-semibold uppercase tracking-wider bg-amber-100 text-amber-800">
                  Official BITS Pilani Ranks
                </Badge>
              </div>
              <p className="text-sm text-slate-500">
                Birla Institute of Technology and Science • Pilani, Goa & Hyderabad Campuses
              </p>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <a
            href="https://admissions.bits-pilani.ac.in/FD/BITSAT_cutOffs.html"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 hover:text-amber-700"
          >
            <Globe className="h-3.5 w-3.5 text-slate-500" />
            Official Portal
            <ExternalLink className="h-3 w-3 text-slate-400" />
          </a>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => scraperMutation.mutate()}
            disabled={scraperMutation.isPending || scraperStatus?.is_running}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${scraperStatus?.is_running ? 'animate-spin text-amber-600' : ''}`} />
            {scraperStatus?.is_running ? 'Scraping Live...' : 'Refresh from Web'}
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowWipeModal(true)}
            className="flex items-center gap-1.5 text-rose-600 hover:bg-rose-50 hover:text-rose-700 border-rose-200"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Reset DB
          </Button>

          <a
            href={getBitsExportUrl(queryParams)}
            download="bitsat_cutoffs.csv"
            className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-2 text-xs font-medium text-white shadow-sm transition-colors hover:bg-amber-700"
          >
            <Download className="h-3.5 w-3.5" />
            Export CSV
          </a>
        </div>
      </div>

      {/* Summary Stats Cards */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-sm">
          <div className="text-xs font-medium text-slate-500">Total Cutoffs</div>
          <div className="mt-1 text-xl font-bold text-slate-900">
            {stats ? formatNumber(stats.total_cutoffs) : '—'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Scraped data points</div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-sm">
          <div className="text-xs font-medium text-slate-500">BITS Campuses</div>
          <div className="mt-1 text-xl font-bold text-amber-700">
            {stats ? stats.total_campuses : '3'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Pilani, Goa, Hyderabad</div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-sm">
          <div className="text-xs font-medium text-slate-500">Academic Years</div>
          <div className="mt-1 text-xl font-bold text-emerald-700">
            {stats ? stats.available_years.length : '2'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">2026-2027 & 2025-2026</div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-sm">
          <div className="text-xs font-medium text-slate-500">Degree Programs</div>
          <div className="mt-1 text-xl font-bold text-slate-900">
            {stats ? stats.total_programs : '19'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">B.E., M.Sc., B.Pharm.</div>
        </div>
      </div>

      {/* Academic Year Selector Bar */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-amber-600" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Select Academic Session Year:
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => updateParam('year', '2026-2027')}
              className={`rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
                yearParam === '2026-2027'
                  ? 'bg-amber-600 text-white shadow-sm ring-2 ring-amber-500 ring-offset-1'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200 hover:text-slate-900'
              }`}
            >
              2026–2027 (Latest)
            </button>

            <button
              onClick={() => updateParam('year', '2025-2026')}
              className={`rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
                yearParam === '2025-2026'
                  ? 'bg-amber-600 text-white shadow-sm ring-2 ring-amber-500 ring-offset-1'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200 hover:text-slate-900'
              }`}
            >
              2025–2026
            </button>

            <button
              onClick={() => updateParam('year', 'ALL')}
              className={`rounded-lg px-3.5 py-1.5 text-xs font-medium transition-all ${
                yearParam === 'ALL'
                  ? 'bg-amber-600 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900'
              }`}
            >
              All Years (Combined)
            </button>
          </div>
        </div>
      </div>

      {/* Filters & Search Panel */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <Filter className="h-4 w-4 text-amber-600" />
            Search & Filter BITSAT Cutoffs
          </div>
          {activeFilters.length > 0 && (
            <button
              onClick={handleClearAllFilters}
              className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-rose-600 transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset Filters
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {/* Year Dropdown */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Academic Year Dropdown
            </label>
            <select
              value={yearParam}
              onChange={(e) => updateParam('year', e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-700 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              <option value="2026-2027">2026–2027</option>
              <option value="2025-2026">2025–2026</option>
              <option value="ALL">All Academic Years</option>
            </select>
          </div>

          {/* Campus Filter with Checkboxes */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              BITS Campus
            </label>
            <SearchableSelect
              placeholder="All 3 BITS Campuses..."
              options={campusOptions}
              multiple={true}
              values={selectedCampuses}
              onMultiChange={(vals) => updateParam('campus', vals.join('||'))}
              wrapLabels={true}
              dropdownClassName="w-auto min-w-[300px] sm:min-w-[380px] max-w-[95vw] shadow-2xl"
            />
          </div>

          {/* Academic Program Filter with Checkboxes & Full Names Clearly Visible */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Academic Program
            </label>
            <SearchableSelect
              placeholder="All Degree Programs..."
              options={programOptions}
              multiple={true}
              values={selectedPrograms}
              onMultiChange={(vals) => updateParam('program', vals.join('||'))}
              wrapLabels={true}
              dropdownClassName="w-auto min-w-[340px] sm:min-w-[480px] max-w-[95vw] shadow-2xl"
            />
          </div>

          {/* Degree Filter */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Degree Type
            </label>
            <select
              value={degreeParam}
              onChange={(e) => updateParam('degree', e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-700 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              <option value="">All Degrees (B.E., M.Sc., B.Pharm.)</option>
              <option value="B.E.">B.E. (Bachelor of Engineering)</option>
              <option value="M.Sc.">M.Sc. (Integrated First Degree)</option>
              <option value="B.Pharm.">B.Pharm. (Pharmacy)</option>
            </select>
          </div>

          {/* Student Score Chance Predictor */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Your BITSAT Score (out of 390)
            </label>
            <div className="relative">
              <input
                type="number"
                min="0"
                max="390"
                placeholder="e.g. 280 (Chance Finder)"
                value={scoreParam}
                onChange={(e) => updateParam('student_score', e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 pl-8 text-xs text-slate-700 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
              />
              <Sparkles className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-amber-500" />
            </div>
          </div>
        </div>

        {/* Active Filter Chips */}
        {activeFilters.length > 0 && (
          <div className="mt-4 pt-3 border-t border-slate-100">
            <FilterChips
              filters={activeFilters}
              onRemove={handleRemoveFilter}
              onClearAll={handleClearAllFilters}
            />
          </div>
        )}
      </div>

      {/* Main Results View Header */}
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-800">
            {cutoffsData ? `${formatNumber(cutoffsData.total)} cutoffs found` : 'Loading cutoffs...'}
          </span>
          {isFetchingCutoffs && (
            <Spinner className="h-4 w-4 text-amber-600" />
          )}
          {scoreParam && (
            <Badge variant="success" className="font-semibold text-xs bg-emerald-100 text-emerald-800">
              Showing options eligible with BITSAT score ≥ {scoreParam}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Sort Selector */}
          <div className="flex items-center gap-1.5 text-xs text-slate-600">
            <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
            <span>Sort:</span>
            <select
              value={sortParam}
              onChange={(e) => updateParam('sort_by', e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-700 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              <option value="score_desc">Cutoff Score: Highest first</option>
              <option value="score_asc">Cutoff Score: Lowest first</option>
              <option value="year_desc">Academic Year: Latest first</option>
              <option value="campus_asc">Campus Name (A → Z)</option>
              <option value="program_asc">Program Name (A → Z)</option>
            </select>
          </div>

          {/* View Mode Toggle */}
          <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-0.5">
            <button
              onClick={() => setViewMode('table')}
              title="Table View"
              className={`rounded-md p-1.5 text-xs font-medium transition-colors ${
                viewMode === 'table' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <TableIcon className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode('cards')}
              title="Card View"
              className={`rounded-md p-1.5 text-xs font-medium transition-colors ${
                viewMode === 'cards' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode('comparison')}
              title="Year Comparison View"
              className={`rounded-md p-1.5 text-xs font-medium transition-colors ${
                viewMode === 'comparison' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <TrendingUp className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Cutoff Content Views */}
      {isLoadingCutoffs ? (
        <div className="flex h-64 items-center justify-center rounded-xl border border-slate-200 bg-white">
          <div className="text-center">
            <Spinner className="h-8 w-8 mx-auto text-amber-600" />
            <p className="mt-2 text-sm text-slate-500">Loading official BITSAT cutoffs...</p>
          </div>
        </div>
      ) : !cutoffsData?.items || cutoffsData.items.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center">
          <Landmark className="h-10 w-10 text-slate-300" />
          <h3 className="mt-2 text-sm font-semibold text-slate-800">No matching cutoffs found</h3>
          <p className="mt-1 text-xs text-slate-500 max-w-sm">
            Try adjusting your search criteria, switching years, or clearing your filters.
          </p>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleClearAllFilters}
            className="mt-4"
          >
            Clear Filters
          </Button>
        </div>
      ) : viewMode === 'table' ? (
        /* TABLE VIEW */
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-slate-700">
                <tr>
                  <th scope="col" className="px-4 py-3.5 font-semibold">
                    Year
                  </th>
                  <th scope="col" className="px-4 py-3.5 font-semibold">
                    Campus
                  </th>
                  <th scope="col" className="px-4 py-3.5 font-semibold">
                    Degree Program
                  </th>
                  <th scope="col" className="px-4 py-3.5 font-semibold">
                    Degree
                  </th>
                  <th scope="col" className="px-4 py-3.5 font-semibold text-right">
                    Cut-off Score
                  </th>
                  <th scope="col" className="px-4 py-3.5 font-semibold text-right">
                    Max Marks
                  </th>
                  <th scope="col" className="px-4 py-3.5 font-semibold text-right">
                    Percentage
                  </th>
                  {scoreParam && (
                    <th scope="col" className="px-4 py-3.5 font-semibold text-center">
                      Eligibility
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {cutoffsData.items.map((item) => {
                  const studentScore = scoreParam ? parseInt(scoreParam, 10) : 0;
                  const isEligible = studentScore > 0 && studentScore >= item.cutoff_score;

                  return (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-50/80 transition-colors"
                    >
                      {/* Year */}
                      <td className="whitespace-nowrap px-4 py-3 font-semibold text-slate-900">
                        <span className="inline-flex items-center rounded-md bg-amber-50 border border-amber-200/80 px-2 py-0.5 text-xs font-semibold text-amber-900">
                          {item.academic_year}
                        </span>
                      </td>

                      {/* Campus */}
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-900">
                          {item.campus_name}
                        </div>
                        <div className="text-[11px] text-slate-400">
                          {item.campus_location || item.campus_state || 'India'}
                        </div>
                      </td>

                      {/* Program */}
                      <td className="px-4 py-3 font-medium text-slate-800">
                        {item.program_name}
                      </td>

                      {/* Degree */}
                      <td className="whitespace-nowrap px-4 py-3">
                        <span
                          className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold ${
                            item.degree_type === 'B.E.'
                              ? 'bg-blue-100 text-blue-800'
                              : item.degree_type === 'B.Pharm.'
                              ? 'bg-purple-100 text-purple-800'
                              : 'bg-emerald-100 text-emerald-800'
                          }`}
                        >
                          {item.degree_type}
                        </span>
                      </td>

                      {/* Cutoff Score */}
                      <td className="whitespace-nowrap px-4 py-3 text-right">
                        <div className="text-sm font-extrabold text-amber-800">
                          {item.cutoff_score}
                        </div>
                      </td>

                      {/* Max Marks */}
                      <td className="whitespace-nowrap px-4 py-3 text-right text-slate-500">
                        {item.max_marks}
                      </td>

                      {/* Percentage */}
                      <td className="whitespace-nowrap px-4 py-3 text-right font-medium text-slate-700">
                        {item.score_percentage !== null ? `${item.score_percentage}%` : '—'}
                      </td>

                      {/* Eligibility Column */}
                      {scoreParam && (
                        <td className="whitespace-nowrap px-4 py-3 text-center">
                          {isEligible ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">
                              <Check className="h-3 w-3" />
                              Admissible
                            </span>
                          ) : (
                            <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                              Short by {item.cutoff_score - studentScore} pts
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

          {/* Pagination */}
          <Pagination
            page={cutoffsData.page}
            pageSize={cutoffsData.page_size}
            total={cutoffsData.total}
            onPageChange={(p) => updateParam('page', p)}
            onPageSizeChange={(ps) => updateParam('page_size', ps)}
            pageSizeOptions={[20, 50, 100, 200]}
          />
        </div>
      ) : viewMode === 'cards' ? (
        /* CARD VIEW */
        <div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {cutoffsData.items.map((item) => {
              const studentScore = scoreParam ? parseInt(scoreParam, 10) : 0;
              const isEligible = studentScore > 0 && studentScore >= item.cutoff_score;

              return (
                <div
                  key={item.id}
                  className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:shadow-md"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <span className="inline-flex items-center rounded-md bg-amber-50 border border-amber-200/80 px-2 py-0.5 text-xs font-semibold text-amber-900">
                        {item.academic_year}
                      </span>
                      <span
                        className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold ${
                          item.degree_type === 'B.E.'
                            ? 'bg-blue-100 text-blue-800'
                            : item.degree_type === 'B.Pharm.'
                            ? 'bg-purple-100 text-purple-800'
                            : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {item.degree_type}
                      </span>
                    </div>

                    <h4 className="text-base font-bold text-slate-900 leading-snug">
                      {item.campus_name}
                    </h4>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {item.campus_location || item.campus_state || 'India'}
                    </p>

                    <div className="mt-3 text-xs font-semibold text-slate-800">
                      {item.program_name}
                    </div>
                  </div>

                  <div className="mt-5 pt-3 border-t border-slate-100 flex items-end justify-between">
                    <div>
                      <div className="text-[11px] text-slate-400">Max Marks</div>
                      <div className="font-semibold text-slate-700 text-xs">
                        {item.max_marks} marks
                      </div>
                      {item.score_percentage !== null && (
                        <div className="text-[10px] text-slate-400">
                          {item.score_percentage}%
                        </div>
                      )}
                    </div>

                    <div className="text-right">
                      <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                        Cutoff Score
                      </div>
                      <div className="text-xl font-extrabold text-amber-700 leading-none mt-0.5">
                        {item.cutoff_score}
                      </div>
                      {scoreParam && isEligible && (
                        <div className="text-[10px] text-emerald-600 font-semibold mt-1">
                          ✓ Admissible
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-6">
            <Pagination
              page={cutoffsData.page}
              pageSize={cutoffsData.page_size}
              total={cutoffsData.total}
              onPageChange={(p) => updateParam('page', p)}
              onPageSizeChange={(ps) => updateParam('page_size', ps)}
              pageSizeOptions={[20, 50, 100, 200]}
            />
          </div>
        </div>
      ) : (
        /* YEAR COMPARISON VIEW (2026-2027 vs 2025-2026) */
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-amber-600" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Year-on-Year Trend (2026–2027 vs 2025–2026)
              </span>
            </div>
            <span className="text-xs text-slate-500">
              Shows how cutoff scores shifted across academic sessions
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-100 text-slate-700">
                <tr>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    BITS Campus
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Degree Program
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Degree
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold text-right">
                    2026–2027
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold text-right">
                    2025–2026
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold text-right">
                    Score Difference
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {comparisonGroups.map((g, idx) => {
                  const s26 = g.score_2026;
                  const s25 = g.score_2025;
                  const diff = (s26 !== undefined && s25 !== undefined) ? s26 - s25 : null;

                  return (
                    <tr key={idx} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3 font-semibold text-slate-900 whitespace-nowrap">
                        {g.campus}
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-800 whitespace-nowrap">
                        {g.program}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="inline-block px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700">
                          {g.degree}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-bold text-amber-800 whitespace-nowrap">
                        {s26 !== undefined ? s26 : '—'}
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-slate-600 whitespace-nowrap">
                        {s25 !== undefined ? s25 : '—'}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold whitespace-nowrap">
                        {diff !== null ? (
                          <span
                            className={
                              diff > 0
                                ? 'text-rose-600 font-bold'
                                : diff < 0
                                ? 'text-emerald-600 font-bold'
                                : 'text-slate-500'
                            }
                          >
                            {diff > 0 ? `+${diff}` : diff}
                          </span>
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Scraper Status / Live Scraping Modal */}
      <Modal
        isOpen={showScraperModal}
        onClose={() => setShowScraperModal(false)}
        title="Official BITSAT Cutoff Web Scraper"
      >
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            {scraperStatus?.is_running ? (
              <Spinner className="h-6 w-6 text-amber-600" />
            ) : scraperStatus?.status === 'COMPLETED' ? (
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
                <CheckCircle2 className="h-5 w-5" />
              </div>
            ) : scraperStatus?.status === 'FAILED' ? (
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-rose-100 text-rose-600">
                <AlertTriangle className="h-5 w-5" />
              </div>
            ) : (
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-slate-600">
                <Info className="h-5 w-5" />
              </div>
            )}
            <div>
              <div className="text-sm font-semibold text-slate-900">
                Status: {scraperStatus?.status || 'IDLE'}
              </div>
              <p className="text-xs text-slate-500">
                {scraperStatus?.message || 'Ready to fetch cutoffs from admissions.bits-pilani.ac.in'}
              </p>
            </div>
          </div>

          {/* Progress Bar */}
          {scraperStatus?.is_running && (
            <div className="space-y-1">
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full bg-amber-600 transition-all duration-300"
                  style={{ width: `${scraperStatus.progress_percent || 15}%` }}
                />
              </div>
              <div className="text-right text-[11px] text-slate-400">
                {scraperStatus.progress_percent}%
              </div>
            </div>
          )}

          <div className="rounded-lg bg-slate-50 p-3 text-xs space-y-1 text-slate-600">
            <div>
              <span className="font-semibold text-slate-700">Source: </span>
              <a
                href="https://admissions.bits-pilani.ac.in/FD/BITSAT_cutOffs.html"
                target="_blank"
                rel="noreferrer"
                className="text-amber-600 hover:underline"
              >
                https://admissions.bits-pilani.ac.in/FD/BITSAT_cutOffs.html
              </a>
            </div>
            <div>
              <span className="font-semibold text-slate-700">Records Scraped: </span>
              {scraperStatus?.records_count || 0}
            </div>
            <div>
              <span className="font-semibold text-slate-700">Years Processed: </span>
              {scraperStatus?.years_count || 0}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            {!scraperStatus?.is_running && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => scraperMutation.mutate()}
                disabled={scraperMutation.isPending}
                className="bg-amber-600 hover:bg-amber-700"
              >
                Run Scraper Now
              </Button>
            )}
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowScraperModal(false)}
            >
              Close
            </Button>
          </div>
        </div>
      </Modal>

      {/* Wipe Database Confirmation Modal */}
      <Modal
        isOpen={showWipeModal}
        onClose={() => setShowWipeModal(false)}
        title="Reset BITS Database"
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <div className="rounded-full bg-rose-100 p-2 text-rose-600">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-900">
                Are you sure you want to reset BITSAT data?
              </h4>
              <p className="mt-1 text-xs text-slate-500 leading-relaxed">
                This will wipe all scraped cutoff records, campuses, and programs from the dedicated BITS database (<code className="font-mono text-slate-700">bits.db</code>).
                Existing JoSAA, MHT-CET, and IISER databases will remain completely untouched.
              </p>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowWipeModal(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => wipeMutation.mutate()}
              disabled={wipeMutation.isPending}
              className="bg-rose-600 hover:bg-rose-700"
            >
              {wipeMutation.isPending ? 'Resetting...' : 'Confirm Reset'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default BitsSearchPage;
