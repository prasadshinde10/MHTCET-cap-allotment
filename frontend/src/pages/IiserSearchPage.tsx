import React, { useState, useMemo, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Search, RotateCcw, Building2, BookOpen, 
  Download, LayoutGrid, Table as TableIcon,
  Award, CheckCircle2, ChevronRight, SlidersHorizontal,
  ExternalLink, ArrowUpDown, Filter, Sparkles,
  Trash2, RefreshCw, AlertTriangle, Globe, School,
  Info, TrendingUp, Layers, Check, Compass, GraduationCap
} from 'lucide-react';
import toast from 'react-hot-toast';

import { 
  getIiserFilterOptions, 
  getIiserCutoffs, 
  getIiserStats,
  getIiserExportUrl,
  scrapeIiserData,
  getIiserScraperStatus,
  resetIiserDatabase,
  IiserCutoffItem,
  IiserScraperStatus
} from '../api/iiser';
import SearchableSelect, { SearchableOption } from '../components/ui/SearchableSelect';
import Select from '../components/ui/Select';
import Button from '../components/ui/Button';
import FilterChips, { ActiveFilter } from '../components/ui/FilterChips';
import Badge from '../components/ui/Badge';
import Spinner from '../components/ui/Spinner';
import Modal from '../components/ui/Modal';
import Pagination from '../components/ui/Pagination';
import { formatNumber } from '../utils/formatters';

export const IiserSearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

  const [showWipeModal, setShowWipeModal] = useState(false);
  const [showScraperModal, setShowScraperModal] = useState(false);
  const [pollScraper, setPollScraper] = useState(false);
  const [viewMode, setViewMode] = useState<'table' | 'cards' | 'progression'>('table');

  // URL state query parameters
  const roundParam = searchParams.get('round') || '';
  const instituteParam = searchParams.get('institute') || '';
  const programParam = searchParams.get('program') || '';
  const degreeParam = searchParams.get('degree') || '';
  const categoryParam = searchParams.get('category') || '';
  const rankParam = searchParams.get('max_rank') || '';
  const sortParam = searchParams.get('sort_by') || 'rank_asc';
  const pageParam = parseInt(searchParams.get('page') || '1', 10);
  const pageSizeParam = parseInt(searchParams.get('page_size') || '50', 10);

  // Multi-select parsed arrays
  const selectedRounds = useMemo(
    () => (roundParam ? roundParam.split(',').map((r) => r.trim()).filter(Boolean) : []),
    [roundParam]
  );
  const selectedInstitutes = useMemo(
    () => (instituteParam ? instituteParam.split('||').map((i) => i.trim()).filter(Boolean) : []),
    [instituteParam]
  );
  const selectedPrograms = useMemo(
    () => (programParam ? programParam.split('||').map((p) => p.trim()).filter(Boolean) : []),
    [programParam]
  );

  // Background Scraper Status Query with automatic 1-second polling while running
  const { data: scraperStatus } = useQuery<IiserScraperStatus>({
    queryKey: ['iiserScraperStatus'],
    queryFn: getIiserScraperStatus,
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
          toast.success(scraperStatus.message || 'IISER cutoffs scraped successfully!');
          queryClient.invalidateQueries({ queryKey: ['iiserFilterOptions'] });
          queryClient.invalidateQueries({ queryKey: ['iiserCutoffs'] });
          queryClient.invalidateQueries({ queryKey: ['iiserStats'] });
        } else if (scraperStatus.status === 'FAILED') {
          toast.error(`IISER scraping failed: ${scraperStatus.error || 'Check server connection'}`);
        }
      }
      prevRunningRef.current = scraperStatus.is_running;
    }
  }, [scraperStatus, queryClient]);

  // Scraper Mutations
  const scraperMutation = useMutation({
    mutationFn: scrapeIiserData,
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message || 'IISER scraper started!');
        setShowScraperModal(true);
        setPollScraper(true);
        queryClient.invalidateQueries({ queryKey: ['iiserScraperStatus'] });
      } else {
        toast.error(data.message);
      }
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.message || 'Failed to start IISER scraper');
    }
  });

  const wipeMutation = useMutation({
    mutationFn: resetIiserDatabase,
    onSuccess: (data) => {
      toast.success(data.message || 'IISER database reset successfully!');
      setShowWipeModal(false);
      queryClient.invalidateQueries({ queryKey: ['iiserFilterOptions'] });
      queryClient.invalidateQueries({ queryKey: ['iiserCutoffs'] });
      queryClient.invalidateQueries({ queryKey: ['iiserStats'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.message || 'Failed to reset IISER database');
    }
  });

  // Fetch Filter Options
  const { data: filterOptions, isLoading: isLoadingFilters } = useQuery({
    queryKey: ['iiserFilterOptions'],
    queryFn: getIiserFilterOptions,
    staleTime: 5 * 60 * 1000,
  });

  // Fetch Database Stats
  const { data: stats } = useQuery({
    queryKey: ['iiserStats'],
    queryFn: getIiserStats,
    staleTime: 60 * 1000,
  });

  // Cutoff Query Params
  const queryParams = useMemo(() => {
    return {
      round_no: roundParam || undefined,
      institute_name: instituteParam || undefined,
      academic_program: programParam || undefined,
      degree_type: degreeParam || undefined,
      category: categoryParam || undefined,
      max_rank: rankParam ? parseInt(rankParam, 10) : undefined,
      sort_by: sortParam,
      page: pageParam,
      page_size: pageSizeParam,
    };
  }, [roundParam, instituteParam, programParam, degreeParam, categoryParam, rankParam, sortParam, pageParam, pageSizeParam]);

  // Fetch Cutoffs
  const { data: cutoffsData, isLoading: isLoadingCutoffs, isFetching: isFetchingCutoffs } = useQuery({
    queryKey: ['iiserCutoffs', queryParams],
    queryFn: () => getIiserCutoffs(queryParams),
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
    if (pageSizeParam !== 50) {
      next.set('page_size', String(pageSizeParam));
    }
    setSearchParams(next);
  };

  // Build searchable options for UI
  const instituteOptions: SearchableOption[] = useMemo(() => {
    if (!filterOptions?.institutes) return [];
    return filterOptions.institutes.map((inst) => ({
      value: inst.institute_name,
      label: inst.institute_name,
      sublabel: inst.state || 'India',
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

  const categoryOptions: SearchableOption[] = useMemo(() => {
    if (!filterOptions?.categories) return [];
    return filterOptions.categories.map((c) => ({
      value: c.category_code,
      label: `${c.category_code} - ${c.category_name}`,
      sublabel: c.is_pwd ? 'PwD Category' : undefined,
    }));
  }, [filterOptions]);

  // Active filter chips
  const activeFilters: ActiveFilter[] = useMemo(() => {
    const list: ActiveFilter[] = [];
    if (selectedRounds.length > 0) {
      if (selectedRounds.length <= 3) {
        selectedRounds.forEach((r) => {
          list.push({ id: `round:${r}`, label: 'Round', value: `Round ${r}` });
        });
      } else {
        list.push({ id: 'round', label: 'Rounds', value: `${selectedRounds.length} Rounds Selected` });
      }
    }
    if (selectedInstitutes.length > 0) {
      if (selectedInstitutes.length <= 2) {
        selectedInstitutes.forEach((inst) => {
          list.push({ id: `institute:${inst}`, label: 'Campus', value: inst });
        });
      } else {
        list.push({ id: 'institute', label: 'Campuses', value: `${selectedInstitutes.length} Campuses Selected` });
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
    if (categoryParam) {
      list.push({ id: 'category', label: 'Category', value: categoryParam });
    }
    if (rankParam) {
      list.push({ id: 'max_rank', label: 'Your Rank ≤', value: rankParam });
    }
    return list;
  }, [selectedRounds, selectedInstitutes, selectedPrograms, degreeParam, categoryParam, rankParam]);

  const handleRemoveFilter = (id: string) => {
    if (id.startsWith('round:')) {
      const rVal = id.replace('round:', '');
      const remaining = selectedRounds.filter((r) => r !== rVal);
      updateParam('round', remaining.join(','));
    } else if (id.startsWith('institute:')) {
      const instVal = id.replace('institute:', '');
      const remaining = selectedInstitutes.filter((i) => i !== instVal);
      updateParam('institute', remaining.join('||'));
    } else if (id.startsWith('program:')) {
      const progVal = id.replace('program:', '');
      const remaining = selectedPrograms.filter((p) => p !== progVal);
      updateParam('program', remaining.join('||'));
    } else {
      updateParam(id, '');
    }
  };

  // Progression grouped view: group by Institute + Program + Category across all rounds
  const progressionGroups = useMemo(() => {
    if (!cutoffsData?.items || viewMode !== 'progression') return [];
    const map = new Map<string, {
      institute: string;
      state?: string | null;
      program: string;
      degree: string;
      category: string;
      rounds: { [round: number]: number };
    }>();

    cutoffsData.items.forEach((item) => {
      const key = `${item.institute_name}__${item.program_name}__${item.category_code}`;
      if (!map.has(key)) {
        map.set(key, {
          institute: item.institute_name,
          state: item.institute_state,
          program: item.program_name,
          degree: item.degree_type,
          category: item.category_code,
          rounds: {},
        });
      }
      map.get(key)!.rounds[item.round_no] = item.closing_rank;
    });

    return Array.from(map.values());
  }, [cutoffsData?.items, viewMode]);

  return (
    <div className="min-h-screen bg-slate-50 p-4 sm:p-6 lg:p-8">
      {/* Header & Title Section */}
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-600 text-white shadow-md shadow-primary-500/20">
              <School className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                  IISER Cutoff Explorer
                </h1>
                <Badge variant="info" className="font-semibold uppercase tracking-wider">
                  Official IAT Ranks
                </Badge>
              </div>
              <p className="text-sm text-slate-500">
                Indian Institutes of Science Education and Research • Overall Closing Ranks
              </p>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <a
            href="https://www.iiseradmission.in/pages/closing_ranks.html"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 hover:text-primary-700"
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
            <RefreshCw className={`h-3.5 w-3.5 ${scraperStatus?.is_running ? 'animate-spin text-primary-600' : ''}`} />
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
            href={getIiserExportUrl(queryParams)}
            download="iiser_cutoffs.csv"
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary-600 px-3 py-2 text-xs font-medium text-white shadow-sm transition-colors hover:bg-primary-700"
          >
            <Download className="h-3.5 w-3.5" />
            Export CSV
          </a>
        </div>
      </div>

      {/* Summary Stats Cards */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-sm">
          <div className="text-xs font-medium text-slate-500">Total Cutoffs</div>
          <div className="mt-1 text-xl font-bold text-slate-900">
            {stats ? formatNumber(stats.total_cutoffs) : '—'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Scraped data points</div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-sm">
          <div className="text-xs font-medium text-slate-500">IISER Campuses</div>
          <div className="mt-1 text-xl font-bold text-primary-700">
            {stats ? stats.total_institutes : '7'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Berhampur, Pune, etc.</div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-sm">
          <div className="text-xs font-medium text-slate-500">Counselling Rounds</div>
          <div className="mt-1 text-xl font-bold text-emerald-700">
            {stats ? stats.total_rounds : '9'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Round 1 to Round 9</div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-sm">
          <div className="text-xs font-medium text-slate-500">Programs</div>
          <div className="mt-1 text-xl font-bold text-slate-900">
            {stats ? stats.total_programs : '—'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">BS-MS, B.Tech, BS</div>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-sm">
          <div className="text-xs font-medium text-slate-500">Categories</div>
          <div className="mt-1 text-xl font-bold text-slate-900">
            {stats ? stats.total_categories : '11'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">UR, EWS, OBC, SC, ST, KM</div>
        </div>
      </div>

      {/* Counselling Rounds Multi-Select Bar with Checkboxes */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-primary-600" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Select CAP Rounds (Checkboxes):
            </span>
            <span className="text-xs text-slate-400 hidden sm:inline">
              Select single or multiple rounds to inspect
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* All Rounds checkbox toggle */}
            <label
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold cursor-pointer transition-all select-none ${
                selectedRounds.length === 0
                  ? 'bg-primary-600 border-primary-600 text-white shadow-sm'
                  : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
              }`}
            >
              <input
                type="checkbox"
                checked={selectedRounds.length === 0}
                onChange={() => updateParam('round', '')}
                className="h-3.5 w-3.5 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
              />
              <span>All Rounds (1–9)</span>
            </label>

            {/* Individual round checkboxes */}
            {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((rNum) => {
              const rStr = String(rNum);
              const isChecked = selectedRounds.includes(rStr);
              return (
                <label
                  key={rNum}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium cursor-pointer transition-all select-none ${
                    isChecked
                      ? 'bg-primary-50 border-primary-300 text-primary-900 font-semibold ring-1 ring-primary-400'
                      : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => {
                      let next: string[];
                      if (isChecked) {
                        next = selectedRounds.filter((r) => r !== rStr);
                      } else {
                        next = [...selectedRounds, rStr].sort((a, b) => parseInt(a, 10) - parseInt(b, 10));
                      }
                      updateParam('round', next.join(','));
                    }}
                    className="h-3.5 w-3.5 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span>Round {rNum}</span>
                </label>
              );
            })}

            {/* Quick reset */}
            {selectedRounds.length > 0 && (
              <button
                type="button"
                onClick={() => updateParam('round', '')}
                className="text-xs text-rose-600 hover:text-rose-700 font-medium underline ml-1"
              >
                Reset to All
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Filters & Search Panel */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <Filter className="h-4 w-4 text-primary-600" />
            Search & Filter IISER Cutoffs
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
          {/* Institute / Campus Filter with Checkboxes */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              IISER Campus / Institute
            </label>
            <SearchableSelect
              placeholder="All 7 IISER Campuses..."
              options={instituteOptions}
              multiple={true}
              values={selectedInstitutes}
              onMultiChange={(vals) => updateParam('institute', vals.join('||'))}
              wrapLabels={true}
              dropdownClassName="w-auto min-w-[320px] sm:min-w-[420px] max-w-[95vw] shadow-2xl"
            />
          </div>

          {/* Academic Program Filter with Checkboxes & Full Names Clearly Visible */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Academic Program
            </label>
            <SearchableSelect
              placeholder="All Academic Programs..."
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
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-700 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              <option value="">All Degrees (BS-MS, B.Tech, BS)</option>
              <option value="BS-MS">BS-MS (Dual Degree)</option>
              <option value="B.Tech">B.Tech (Engineering Sciences)</option>
              <option value="BS">BS (Economic Sciences)</option>
            </select>
          </div>

          {/* Category Filter */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Category
            </label>
            <SearchableSelect
              placeholder="All Categories (UR, EWS, OBC, SC...)"
              options={categoryOptions}
              value={categoryParam}
              onChange={(val) => updateParam('category', val)}
            />
          </div>

          {/* Student Rank Chance Predictor */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Your IAT Overall Rank
            </label>
            <div className="relative">
              <input
                type="number"
                placeholder="e.g. 3500 (Chance Finder)"
                value={rankParam}
                onChange={(e) => updateParam('max_rank', e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 pl-8 text-xs text-slate-700 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
              <Sparkles className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-primary-500" />
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
            <Spinner className="h-4 w-4 text-primary-600" />
          )}
          {rankParam && (
            <Badge variant="success" className="font-semibold text-xs">
              Filtering options where closing rank ≥ {formatNumber(parseInt(rankParam, 10))}
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
              className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-700 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              <option value="rank_asc">Closing Rank: Lowest first</option>
              <option value="rank_desc">Closing Rank: Highest first</option>
              <option value="round_desc">Round: Latest first (Round 9 → 1)</option>
              <option value="round_asc">Round: Earliest first (Round 1 → 9)</option>
              <option value="institute_asc">Institute Name (A → Z)</option>
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
              onClick={() => setViewMode('progression')}
              title="Round Comparison View"
              className={`rounded-md p-1.5 text-xs font-medium transition-colors ${
                viewMode === 'progression' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
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
            <Spinner className="h-8 w-8 mx-auto text-primary-600" />
            <p className="mt-2 text-sm text-slate-500">Loading official IISER cutoffs...</p>
          </div>
        </div>
      ) : !cutoffsData?.items || cutoffsData.items.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center">
          <School className="h-10 w-10 text-slate-300" />
          <h3 className="mt-2 text-sm font-semibold text-slate-800">No matching cutoffs found</h3>
          <p className="mt-1 text-xs text-slate-500 max-w-sm">
            Try adjusting your filters, selecting a different round, or resetting your search.
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
                    Round
                  </th>
                  <th scope="col" className="px-4 py-3.5 font-semibold">
                    IISER Campus
                  </th>
                  <th scope="col" className="px-4 py-3.5 font-semibold">
                    Academic Program
                  </th>
                  <th scope="col" className="px-4 py-3.5 font-semibold">
                    Degree
                  </th>
                  <th scope="col" className="px-4 py-3.5 font-semibold">
                    Category
                  </th>
                  <th scope="col" className="px-4 py-3.5 font-semibold text-right">
                    Closing Rank (Overall)
                  </th>
                  {rankParam && (
                    <th scope="col" className="px-4 py-3.5 font-semibold text-center">
                      Eligibility
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {cutoffsData.items.map((item) => {
                  const studentRank = rankParam ? parseInt(rankParam, 10) : 0;
                  const isEligible = studentRank > 0 && studentRank <= item.closing_rank;

                  return (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-50/80 transition-colors"
                    >
                      {/* Round */}
                      <td className="whitespace-nowrap px-4 py-3 font-semibold text-slate-900">
                        <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">
                          Round {item.round_no}
                        </span>
                      </td>

                      {/* Institute */}
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-900">
                          {item.institute_name}
                        </div>
                        <div className="text-[11px] text-slate-400">
                          {item.institute_state || 'India'}
                        </div>
                      </td>

                      {/* Program */}
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-800">
                          {item.program_name}
                        </div>
                        <div className="text-[11px] text-slate-400">
                          Channel: {item.allocation_channel} • Seat Pool: {item.seat_pool}
                        </div>
                      </td>

                      {/* Degree */}
                      <td className="whitespace-nowrap px-4 py-3">
                        <span
                          className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold ${
                            item.degree_type === 'B.Tech'
                              ? 'bg-amber-100 text-amber-800'
                              : item.degree_type === 'BS'
                              ? 'bg-indigo-100 text-indigo-800'
                              : 'bg-primary-100 text-primary-800'
                          }`}
                        >
                          {item.degree_type}
                        </span>
                      </td>

                      {/* Category */}
                      <td className="whitespace-nowrap px-4 py-3">
                        <div className="font-semibold text-slate-800">
                          {item.category_code}
                        </div>
                        {item.is_pwd && (
                          <span className="inline-block text-[10px] text-purple-700 font-semibold bg-purple-50 rounded px-1">
                            PwD
                          </span>
                        )}
                      </td>

                      {/* Closing Rank */}
                      <td className="whitespace-nowrap px-4 py-3 text-right">
                        <div className="text-sm font-bold text-slate-900">
                          {formatNumber(item.closing_rank)}
                        </div>
                        <div className="text-[10px] text-slate-400">
                          IAT Overall Rank
                        </div>
                      </td>

                      {/* Eligibility Column (if student rank entered) */}
                      {rankParam && (
                        <td className="whitespace-nowrap px-4 py-3 text-center">
                          {isEligible ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">
                              <Check className="h-3 w-3" />
                              Likely Admit
                            </span>
                          ) : (
                            <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                              Cutoff higher
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
              const studentRank = rankParam ? parseInt(rankParam, 10) : 0;
              const isEligible = studentRank > 0 && studentRank <= item.closing_rank;

              return (
                <div
                  key={item.id}
                  className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:shadow-md"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">
                        Round {item.round_no}
                      </span>
                      <span
                        className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold ${
                          item.degree_type === 'B.Tech'
                            ? 'bg-amber-100 text-amber-800'
                            : item.degree_type === 'BS'
                            ? 'bg-indigo-100 text-indigo-800'
                            : 'bg-primary-100 text-primary-800'
                        }`}
                      >
                        {item.degree_type}
                      </span>
                    </div>

                    <h4 className="text-base font-bold text-slate-900 leading-snug">
                      {item.institute_name}
                    </h4>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {item.institute_state || 'India'}
                    </p>

                    <div className="mt-3 text-xs font-medium text-slate-800">
                      {item.program_name}
                    </div>
                  </div>

                  <div className="mt-5 pt-3 border-t border-slate-100 flex items-end justify-between">
                    <div>
                      <div className="text-[11px] text-slate-400">Category</div>
                      <div className="font-semibold text-slate-800 text-xs">
                        {item.category_code}
                        {item.is_pwd && ' (PwD)'}
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                        Closing Rank
                      </div>
                      <div className="text-lg font-extrabold text-primary-700 leading-none mt-0.5">
                        {formatNumber(item.closing_rank)}
                      </div>
                      {rankParam && isEligible && (
                        <div className="text-[10px] text-emerald-600 font-semibold mt-1">
                          ✓ Rank fits cutoff
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
        /* PROGRESSION / ROUND-BY-ROUND COMPARISON VIEW */
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-primary-600" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Round-by-Round Progression Matrix (Rounds 1 → 9)
              </span>
            </div>
            <span className="text-xs text-slate-500">
              Shows how cutoffs expanded across rounds
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-100 text-slate-700">
                <tr>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Institute & Campus
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Program & Degree
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Category
                  </th>
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((r) => (
                    <th key={r} scope="col" className="px-3 py-3 font-semibold text-right">
                      R{r}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {progressionGroups.map((g, idx) => (
                  <tr key={idx} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-2.5 font-semibold text-slate-900 whitespace-nowrap">
                      {g.institute}
                    </td>
                    <td className="px-4 py-2.5 text-slate-800 whitespace-nowrap">
                      {g.program}
                    </td>
                    <td className="px-4 py-2.5 font-semibold text-slate-700 whitespace-nowrap">
                      {g.category}
                    </td>
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((r) => {
                      const rank = g.rounds[r];
                      return (
                        <td key={r} className="px-3 py-2.5 text-right font-medium whitespace-nowrap">
                          {rank ? (
                            <span className="text-slate-900 font-semibold">
                              {formatNumber(rank)}
                            </span>
                          ) : (
                            <span className="text-slate-300">—</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Scraper Status / Live Scraping Modal */}
      <Modal
        isOpen={showScraperModal}
        onClose={() => setShowScraperModal(false)}
        title="Official IISER Cutoff Web Scraper"
      >
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            {scraperStatus?.is_running ? (
              <Spinner className="h-6 w-6 text-primary-600" />
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
                {scraperStatus?.message || 'Ready to fetch cutoffs from iiseradmission.in'}
              </p>
            </div>
          </div>

          {/* Progress Bar */}
          {scraperStatus?.is_running && (
            <div className="space-y-1">
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full bg-primary-600 transition-all duration-300"
                  style={{ width: `${scraperStatus.progress_percent || 10}%` }}
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
                href="https://www.iiseradmission.in/pages/closing_ranks.html"
                target="_blank"
                rel="noreferrer"
                className="text-primary-600 hover:underline"
              >
                https://www.iiseradmission.in/pages/closing_ranks.html
              </a>
            </div>
            <div>
              <span className="font-semibold text-slate-700">Records Scraped: </span>
              {scraperStatus?.records_count || 0}
            </div>
            <div>
              <span className="font-semibold text-slate-700">Rounds Processed: </span>
              {scraperStatus?.total_rounds || 0}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            {!scraperStatus?.is_running && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => scraperMutation.mutate()}
                disabled={scraperMutation.isPending}
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
        title="Reset IISER Database"
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <div className="rounded-full bg-rose-100 p-2 text-rose-600">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-900">
                Are you sure you want to reset IISER data?
              </h4>
              <p className="mt-1 text-xs text-slate-500 leading-relaxed">
                This will wipe all scraped cutoff records, programs, categories, and round notices from the dedicated IISER database (<code className="font-mono text-slate-700">iiser.db</code>).
                Existing JoSAA and MHT-CET databases will remain completely untouched.
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

export default IiserSearchPage;
