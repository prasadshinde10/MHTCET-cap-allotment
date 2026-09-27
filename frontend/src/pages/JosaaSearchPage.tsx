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
  Trash2, RefreshCw, AlertTriangle
} from 'lucide-react';
import SearchableSelect, { SearchableOption } from '../components/ui/SearchableSelect';
import Select from '../components/ui/Select';
import Button from '../components/ui/Button';
import FilterChips, { ActiveFilter } from '../components/ui/FilterChips';
import Badge from '../components/ui/Badge';
import Spinner from '../components/ui/Spinner';
import toast from 'react-hot-toast';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { resetJosaaDatabase, reloadJosaaData } from '../api/josaa';

export const JosaaSearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const [showWipeModal, setShowWipeModal] = useState(false);

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
    mutationFn: reloadJosaaData,
    onSuccess: (data) => {
      toast.success(data.message || 'JoSAA data restored successfully!');
      queryClient.invalidateQueries({ queryKey: ['josaaFilterOptions'] });
      queryClient.invalidateQueries({ queryKey: ['josaaCutoffs'] });
      queryClient.invalidateQueries({ queryKey: ['josaaStats'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.message || 'Failed to reload JoSAA data');
    }
  });

  // Filter states
  const [roundNo, setRoundNo] = useState<string>(searchParams.get('round') || '');
  const [instituteType, setInstituteType] = useState<string>(searchParams.get('type') || '');
  const [selectedInstitutes, setSelectedInstitutes] = useState<string[]>(() => {
    const p = searchParams.get('institute');
    return p ? p.split(',').map((s) => s.trim()).filter(Boolean) : [];
  });
  const [selectedPrograms, setSelectedPrograms] = useState<string[]>(() => {
    const p = searchParams.get('program');
    return p ? p.split(',').map((s) => s.trim()).filter(Boolean) : [];
  });
  const [category, setCategory] = useState<string>(searchParams.get('category') || '');
  const [quota, setQuota] = useState<string>(searchParams.get('quota') || '');
  const [gender, setGender] = useState<string>(searchParams.get('gender') || '');
  const [academicYear, setAcademicYear] = useState<string>(searchParams.get('year') || '2025');
  const [candidateRank, setCandidateRank] = useState<string>(searchParams.get('rank') || '');

  // UI state
  const [hasSearched, setHasSearched] = useState(false);
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');
  const [sortBy, setSortBy] = useState<'rank_asc' | 'rank_desc' | 'opening_rank_asc' | 'institute' | 'program'>('rank_asc');
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(50);

  // Sync from URL params on load
  useEffect(() => {
    const roundParam = searchParams.get('round');
    const typeParam = searchParams.get('type');
    const instParam = searchParams.get('institute');
    const progParam = searchParams.get('program');
    const catParam = searchParams.get('category');
    const quotaParam = searchParams.get('quota');
    const genParam = searchParams.get('gender');
    const yrParam = searchParams.get('year');
    const rkParam = searchParams.get('rank');

    const hasAny = Boolean(roundParam || typeParam || instParam || progParam || catParam || quotaParam || genParam || yrParam || rkParam);
    if (hasAny) {
      if (roundParam !== null) setRoundNo(roundParam);
      if (typeParam !== null) setInstituteType(typeParam);
      if (instParam !== null) setSelectedInstitutes(instParam ? instParam.split(',').map((s) => s.trim()).filter(Boolean) : []);
      if (progParam !== null) setSelectedPrograms(progParam ? progParam.split(',').map((s) => s.trim()).filter(Boolean) : []);
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
    if (filterOptions?.rounds) {
      filterOptions.rounds.forEach((r) => {
        list.push({ value: String(r), label: `Round ${r}` });
      });
    } else {
      for (let i = 1; i <= 6; i++) {
        list.push({ value: String(i), label: `Round ${i}` });
      }
    }
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

  // Quota options
  const quotaOptions = useMemo(() => {
    const list = [{ value: '', label: 'All Quotas (AI, HS, OS)' }];
    if (filterOptions?.quotas) {
      filterOptions.quotas.forEach((q) => {
        let label = q;
        if (q === 'AI') label = 'AI (All India Quota)';
        else if (q === 'HS') label = 'HS (Home State Quota)';
        else if (q === 'OS') label = 'OS (Other State Quota)';
        list.push({ value: q, label });
      });
    }
    return list;
  }, [filterOptions]);

  // Query cutoffs
  const queryParams = useMemo(() => ({
    round_no: roundNo ? Number(roundNo) : undefined,
    institute_type: instituteType || undefined,
    institute_name: selectedInstitutes.length > 0 ? selectedInstitutes.join(',') : undefined,
    academic_program: selectedPrograms.length > 0 ? selectedPrograms.join(',') : undefined,
    category: category || undefined,
    quota: quota || undefined,
    gender: gender || undefined,
    academic_year: academicYear ? Number(academicYear) : undefined,
    max_rank: candidateRank ? Number(candidateRank) : undefined,
    page,
    page_size: pageSize,
    sort_by: sortBy,
  }), [roundNo, instituteType, selectedInstitutes, selectedPrograms, category, quota, gender, academicYear, candidateRank, page, pageSize, sortBy]);

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
    if (roundNo) params.set('round', roundNo);
    if (instituteType) params.set('type', instituteType);
    if (selectedInstitutes.length > 0) params.set('institute', selectedInstitutes.join(','));
    if (selectedPrograms.length > 0) params.set('program', selectedPrograms.join(','));
    if (category) params.set('category', category);
    if (quota) params.set('quota', quota);
    if (gender) params.set('gender', gender);
    if (academicYear) params.set('year', academicYear);
    if (candidateRank) params.set('rank', candidateRank);

    setSearchParams(params);
  };

  // Reset Filters
  const handleReset = () => {
    setRoundNo('');
    setInstituteType('');
    setSelectedInstitutes([]);
    setSelectedPrograms([]);
    setCategory('');
    setQuota('');
    setGender('');
    setCandidateRank('');
    setHasSearched(false);
    setPage(1);
    setSearchParams(new URLSearchParams());
    toast.success('Filters reset');
  };

  // Active filter chips
  const activeFilterChips: ActiveFilter[] = useMemo(() => {
    const chips: ActiveFilter[] = [];
    if (roundNo) chips.push({ id: 'round', label: 'Round', value: `Round ${roundNo}` });
    if (instituteType) chips.push({ id: 'type', label: 'Type', value: instituteType });
    if (selectedInstitutes.length > 0) {
      chips.push({
        id: 'institute',
        label: 'Institute',
        value: selectedInstitutes.length === 1 ? selectedInstitutes[0] : `${selectedInstitutes.length} Institutes`,
      });
    }
    if (selectedPrograms.length > 0) {
      chips.push({
        id: 'program',
        label: 'Program',
        value: selectedPrograms.length === 1 ? selectedPrograms[0] : `${selectedPrograms.length} Programs`,
      });
    }
    if (category) chips.push({ id: 'category', label: 'Category', value: category });
    if (quota) chips.push({ id: 'quota', label: 'Quota', value: quota });
    if (gender) chips.push({ id: 'gender', label: 'Pool', value: gender });
    if (candidateRank) chips.push({ id: 'rank', label: 'JEE Rank ≤', value: `#${candidateRank}` });
    return chips;
  }, [roundNo, instituteType, selectedInstitutes, selectedPrograms, category, quota, gender, candidateRank]);

  const removeFilterChip = (id: string) => {
    if (id === 'round') setRoundNo('');
    if (id === 'type') setInstituteType('');
    if (id === 'institute') setSelectedInstitutes([]);
    if (id === 'program') setSelectedPrograms([]);
    if (id === 'category') setCategory('');
    if (id === 'quota') setQuota('');
    if (id === 'gender') setGender('');
    if (id === 'rank') setCandidateRank('');
  };

  // Institute Type styling helper
  const getInstituteTypeBadge = (type: string) => {
    switch (type.toUpperCase()) {
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

            <Button
              variant="outline"
              size="sm"
              onClick={() => reloadMutation.mutate()}
              disabled={reloadMutation.isPending}
              className="text-xs text-indigo-300 border-indigo-700/60 hover:bg-indigo-950/60"
              title="Restore official institutes registry and sample cutoffs"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${reloadMutation.isPending ? 'animate-spin' : ''}`} />
              Restore Data
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
              <p>3. You can click "Restore Data" anytime to reload the official institute registry and cutoffs.</p>
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
            <Select
              label="JoSAA Round"
              value={roundNo}
              onChange={(e) => setRoundNo(e.target.value)}
              options={roundSelectOptions}
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

          {/* Row 3: Seat Pool / Gender, Candidate JEE Rank, Year */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
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
              options={
                filterOptions?.years?.map((y) => ({ value: String(y), label: `${y} Cutoffs` })) || [
                  { value: '2025', label: '2025 Cutoffs' },
                ]
              }
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
                            <span className="font-semibold text-xs text-slate-800 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded">
                              {row.quota}
                            </span>
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
                          <span>Quota: <strong className="text-slate-700">{row.quota}</strong></span>
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
