import React, { useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { 
  Building2, BookOpen, Download, LayoutGrid, Table as TableIcon,
  Filter, Sparkles, RefreshCw, Stethoscope, Activity, Calendar,
  Layers, HelpCircle
} from 'lucide-react';
import toast from 'react-hot-toast';

import { 
  getMedicalFilterOptions, 
  getMedicalCutoffs, 
  getMedicalStats,
  getMedicalExportUrl,
  MedicalCutoffItem,
} from '../api/medical';
import SearchableSelect, { SearchableOption } from '../components/ui/SearchableSelect';
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

  // URL state query parameters
  const yearParam = searchParams.get('year') || '2026-2027'; // Default to latest year
  const roundParam = searchParams.get('round') || '';
  const collegeParam = searchParams.get('college') || '';
  const courseParam = searchParams.get('course') || '';
  const collegeTypeParam = searchParams.get('type') || '';
  const categoryParam = searchParams.get('category') || '';
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

  // Filter options query
  const { data: filterOptions, isLoading: isOptionsLoading } = useQuery({
    queryKey: ['medicalFilterOptions'],
    queryFn: getMedicalFilterOptions,
  });

  // Database stats query
  const { data: dbStats, isLoading: isStatsLoading } = useQuery({
    queryKey: ['medicalStats'],
    queryFn: getMedicalStats,
  });

  // Query cutoffs
  const queryArgs = useMemo(() => {
    return {
      academic_year: yearParam === 'ALL' ? undefined : yearParam,
      round_name: roundParam || undefined,
      college_name: collegeParam || undefined,
      course_name: courseParam || undefined,
      college_type: collegeTypeParam || undefined,
      category: categoryParam || undefined,
      student_rank: rankParam ? parseInt(rankParam, 10) : undefined,
      student_score: scoreParam ? parseInt(scoreParam, 10) : undefined,
      page: pageParam,
      page_size: pageSizeParam,
      sort_by: sortParam,
    };
  }, [
    yearParam, roundParam, collegeParam, courseParam, collegeTypeParam,
    categoryParam, rankParam, scoreParam, pageParam, pageSizeParam, sortParam
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

  const clearAllFilters = () => {
    const nextParams = new URLSearchParams();
    nextParams.set('year', '2026-2027');
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
      sublabel: `${c.college_type || 'College'} • ${c.city || 'Maharashtra'}`,
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
    if (categoryParam) {
      filters.push({
        id: 'category',
        label: 'Category',
        value: categoryParam,
      });
    }
    if (rankParam) {
      filters.push({
        id: 'rank',
        label: 'NEET AIR ≤',
        value: formatNumber(parseInt(rankParam, 10)),
      });
    }
    if (scoreParam) {
      filters.push({
        id: 'score',
        label: 'NEET Score ≥',
        value: `${scoreParam} / 720`,
      });
    }
    return filters;
  }, [
    yearParam, roundParam, selectedCourses, selectedColleges,
    collegeTypeParam, categoryParam, rankParam, scoreParam
  ]);

  const handleRemoveFilter = (filterId: string) => {
    if (filterId === 'year') updateQueryParam('year', 'ALL');
    else if (filterId === 'round') updateQueryParam('round', null);
    else if (filterId === 'college_type') updateQueryParam('type', null);
    else if (filterId === 'category') updateQueryParam('category', null);
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
              State Common Entrance Test Cell • NEET (UG) Counselling
            </div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-white flex items-center gap-3">
              Maharashtra Medical & AYUSH Cutoffs
            </h1>
            <p className="text-emerald-100 text-sm max-w-3xl leading-relaxed">
              Explore official NEET-UG allotment cutoffs across Government & Private Medical, Dental, Ayurvedic, Homeopathic, Physiotherapy & Nursing Colleges in Maharashtra.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
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
              onClick={() => queryClient.invalidateQueries({ queryKey: ['medicalCutoffs'] })}
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
              Colleges
            </div>
            <div className="text-xl font-bold text-white mt-1">
              {isStatsLoading ? '...' : formatNumber(dbStats?.college_count || 0)}
            </div>
            <div className="text-[11px] text-emerald-200 mt-0.5">
              Govt & Private Health Institutes
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur rounded-xl p-3.5 border border-white/15">
            <div className="text-xs font-medium text-emerald-100 flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5" />
              Courses
            </div>
            <div className="text-xl font-bold text-white mt-1">
              {isStatsLoading ? '...' : (dbStats?.course_count || 8)}
            </div>
            <div className="text-[11px] text-emerald-200 mt-0.5">
              MBBS, BDS, BAMS, BHMS, PT...
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur rounded-xl p-3.5 border border-white/15">
            <div className="text-xs font-medium text-emerald-100 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5" />
              Cutoff Records
            </div>
            <div className="text-xl font-bold text-white mt-1">
              {isStatsLoading ? '...' : formatNumber(dbStats?.cutoff_count || 0)}
            </div>
            <div className="text-[11px] text-emerald-200 mt-0.5">
              Quotawise AIR & NEET Marks
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur rounded-xl p-3.5 border border-white/15">
            <div className="text-xs font-medium text-emerald-100 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" />
              Academic Years
            </div>
            <div className="text-xl font-bold text-white mt-1">
              {isStatsLoading ? '...' : (dbStats?.years?.length || 3)}
            </div>
            <div className="text-[11px] text-emerald-200 mt-0.5">
              2026-27, 2025-26, 2024-25
            </div>
          </div>
        </div>
      </div>

      {/* NEET Rank & Marks Predictor Box (Light Theme) */}
      <div className="bg-gradient-to-r from-emerald-50 via-teal-50/60 to-white border border-emerald-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-emerald-800 font-semibold text-sm">
              <Sparkles className="w-4 h-4 text-emerald-600" />
              NEET (UG) Rank & Marks Eligibility Predictor
            </div>
            <p className="text-xs text-slate-600">
              Enter your NEET All India Rank (AIR) or Score (out of 720) to instantly highlight matching medical colleges where you are eligible.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-700 whitespace-nowrap">Your NEET AIR:</span>
              <input
                type="number"
                placeholder="e.g. 15400"
                value={rankParam}
                onChange={(e) => updateQueryParam('student_rank', e.target.value ? e.target.value : null)}
                className="w-32 bg-white border border-emerald-300 rounded-lg px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs placeholder-slate-400"
              />
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-700 whitespace-nowrap">Your NEET Score:</span>
              <input
                type="number"
                placeholder="e.g. 620"
                min="0"
                max="720"
                value={scoreParam}
                onChange={(e) => updateQueryParam('student_score', e.target.value ? e.target.value : null)}
                className="w-28 bg-white border border-emerald-300 rounded-lg px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs placeholder-slate-400"
              />
            </div>

            {(rankParam || scoreParam) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  updateQueryParam('student_rank', null);
                  updateQueryParam('student_score', null);
                }}
                className="text-xs text-slate-500 hover:text-slate-800"
              >
                Clear Score
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Filter Section (Light Theme) */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4 shadow-xs">
        <div className="flex items-center justify-between pb-2 border-b border-slate-100">
          <div className="flex items-center gap-2 text-slate-800 font-semibold text-sm">
            <Filter className="w-4 h-4 text-emerald-600" />
            Medical Filters & Search Criteria
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllFilters}
              className="text-xs text-slate-500 hover:text-emerald-700"
            >
              Reset All
            </Button>
          </div>
        </div>

        {/* Filter Inputs Grid */}
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

          {/* CAP Round */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Counselling Round</label>
            <select
              value={roundParam}
              onChange={(e) => updateQueryParam('round', e.target.value || null)}
              className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs"
            >
              <option value="">All Rounds</option>
              {filterOptions?.rounds.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>

          {/* College Type */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">College Management</label>
            <select
              value={collegeTypeParam}
              onChange={(e) => updateQueryParam('type', e.target.value || null)}
              className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs"
            >
              <option value="">All Management Types</option>
              <option value="Government/Aided">Government / Aided Colleges</option>
              <option value="Private">Private / Unaided Colleges</option>
            </select>
          </div>

          {/* Category Filter */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Category / Quota</label>
            <select
              value={categoryParam}
              onChange={(e) => updateQueryParam('category', e.target.value || null)}
              className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-500 shadow-xs"
            >
              <option value="">All Categories</option>
              {categoriesList.map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Second Row: Course and College Multi-selects */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          {/* Courses Searchable Select */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Medical Course (MBBS, BDS, BAMS, BHMS, BPTH, etc.)
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
              Medical College Name / Code
            </label>
            <SearchableSelect
              placeholder="All Medical Colleges..."
              options={collegeOptions}
              multiple={true}
              values={selectedColleges}
              onMultiChange={(vals) => updateQueryParam('college', vals.length > 0 ? vals.join('||') : null)}
            />
          </div>
        </div>

        {/* Quick Course Badges */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-xs text-slate-500 mr-1">Quick Courses:</span>
          {['MBBS', 'BDS', 'BAMS', 'BHMS', 'BPTH', 'B.Sc. Nursing'].map((c) => {
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
                    {(rankParam || scoreParam) && (
                      <th className="py-3.5 px-3 font-semibold text-center">Chance</th>
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
                                    row.college_type === 'Government/Aided' 
                                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium' 
                                      : 'bg-slate-100 text-slate-600'
                                  }`}>
                                    {row.college_type}
                                  </span>
                                  {row.city && <span>• {row.city}</span>}
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
                            <div className="font-medium text-slate-900">
                              {row.quota_category}
                            </div>
                            <div className="text-[10px] text-slate-500">
                              Base: {row.base_category}
                            </div>
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
                          {(rankParam || scoreParam) && (
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
