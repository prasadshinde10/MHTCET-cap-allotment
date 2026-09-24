import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getCutoffs, exportCutoffs, CutoffFilters } from '../api/cutoffs';
import { getFilterOptions, getCutoffSummary } from '../api/analysis';
import { 
  Download, Filter, RotateCcw, Building2, BookOpen, 
  Search, SlidersHorizontal, ChevronDown, ChevronUp, FileText, CheckCircle2
} from 'lucide-react';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Spinner from '../components/ui/Spinner';
import Select from '../components/ui/Select';
import Pagination from '../components/ui/Pagination';
import toast from 'react-hot-toast';

export function CutoffsPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [isExporting, setIsExporting] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(true);

  // Filter states
  const [year, setYear] = useState<string>('2026');
  const [roundNumber, setRoundNumber] = useState<string>('');
  const [collegeSearch, setCollegeSearch] = useState<string>('');
  const [courseSearch, setCourseSearch] = useState<string>('');
  const [categoryCode, setCategoryCode] = useState<string>('');
  const [gender, setGender] = useState<string>('');
  const [cityDistrict, setCityDistrict] = useState<string>('');
  const [seatSection, setSeatSection] = useState<string>('');
  const [stage, setStage] = useState<string>('');
  const [minPercentile, setMinPercentile] = useState<string>('');
  const [maxPercentile, setMaxPercentile] = useState<string>('');
  const [minMerit, setMinMerit] = useState<string>('');
  const [maxMerit, setMaxMerit] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('percentile_desc');

  // Load dynamic filter options from database
  const { data: filterOptions } = useQuery({
    queryKey: ['filterOptions'],
    queryFn: getFilterOptions,
    staleTime: 60000,
  });

  // Query parameters object
  const queryParams: CutoffFilters = useMemo(() => ({
    page,
    page_size: pageSize,
    year: year ? Number(year) : undefined,
    round_number: roundNumber ? Number(roundNumber) : undefined,
    college: collegeSearch || undefined,
    course: courseSearch || undefined,
    category_code: categoryCode || undefined,
    gender: gender || undefined,
    city_district: cityDistrict || undefined,
    seat_section: seatSection || undefined,
    stage: stage || undefined,
    min_percentile: minPercentile ? Number(minPercentile) : undefined,
    max_percentile: maxPercentile ? Number(maxPercentile) : undefined,
    min_merit: minMerit ? Number(minMerit) : undefined,
    max_merit: maxMerit ? Number(maxMerit) : undefined,
    sort_by: sortBy,
    is_deleted: false,
  }), [
    page, pageSize, year, roundNumber, collegeSearch, courseSearch,
    categoryCode, gender, cityDistrict, seatSection, stage,
    minPercentile, maxPercentile, minMerit, maxMerit, sortBy
  ]);

  // Fetch paginated cutoffs
  const { data, isLoading } = useQuery({
    queryKey: ['cutoffs', queryParams],
    queryFn: () => getCutoffs(queryParams),
  });

  // Fetch aggregate analysis summary for current filters
  const { data: summary } = useQuery({
    queryKey: ['cutoffSummary', queryParams],
    queryFn: () => getCutoffSummary(queryParams),
  });

  const handleResetFilters = () => {
    setYear('2026');
    setRoundNumber('');
    setCollegeSearch('');
    setCourseSearch('');
    setCategoryCode('');
    setGender('');
    setCityDistrict('');
    setSeatSection('');
    setStage('');
    setMinPercentile('');
    setMaxPercentile('');
    setMinMerit('');
    setMaxMerit('');
    setSortBy('percentile_desc');
    setPage(1);
    toast.success('Filters reset to default');
  };

  const handleQuickPercentile = (min?: number, max?: number) => {
    setMinPercentile(min !== undefined ? min.toString() : '');
    setMaxPercentile(max !== undefined ? max.toString() : '');
    setPage(1);
  };

  const handleExport = async () => {
    try {
      setIsExporting(true);
      const blob = await exportCutoffs(queryParams);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `CAP_Cutoff_Analysis_${year || 'All'}_Round${roundNumber || 'All'}_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Cutoffs CSV exported successfully');
    } catch {
      toast.error('Failed to export CSV');
    } finally {
      setIsExporting(false);
    }
  };

  const cutoffItems = data?.items || [];

  const getPercentileBadgeClass = (val?: number) => {
    if (val === undefined || val === null) return 'bg-gray-100 text-gray-700 border-gray-200';
    if (val >= 95) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    if (val >= 90) return 'bg-blue-50 text-blue-700 border-blue-200';
    if (val >= 80) return 'bg-purple-50 text-purple-700 border-purple-200';
    return 'bg-amber-50 text-amber-700 border-amber-200';
  };

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (roundNumber) count++;
    if (collegeSearch) count++;
    if (courseSearch) count++;
    if (categoryCode) count++;
    if (gender) count++;
    if (cityDistrict) count++;
    if (seatSection) count++;
    if (stage) count++;
    if (minPercentile || maxPercentile) count++;
    if (minMerit || maxMerit) count++;
    return count;
  }, [roundNumber, collegeSearch, courseSearch, categoryCode, gender, cityDistrict, seatSection, stage, minPercentile, maxPercentile, minMerit, maxMerit]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Cutoff Analysis</h1>
            <Badge variant="success" className="gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> PDF Source of Truth
            </Badge>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Analyze official CAP Round allotments extracted page-by-page via PyMuPDF. Purely data-driven with no manual estimation.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button 
            onClick={handleResetFilters} 
            variant="secondary" 
            size="sm" 
            className="gap-1.5 text-gray-600"
          >
            <RotateCcw className="w-4 h-4" /> Reset
          </Button>

          <Button 
            onClick={handleExport} 
            variant="primary" 
            size="sm" 
            isLoading={isExporting} 
            className="gap-1.5"
          >
            <Download className="w-4 h-4" /> Export CSV
          </Button>
        </div>
      </div>

      {/* KPI Analytical Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Matching Allotments</p>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-extrabold text-gray-900 font-mono">
              {summary ? summary.total_matches.toLocaleString() : '—'}
            </span>
            <span className="text-xs text-gray-400">records</span>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Colleges & Courses</p>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-extrabold text-blue-600 font-mono">
              {summary?.unique_colleges || 0}
            </span>
            <span className="text-xs text-gray-400">institutes /</span>
            <span className="text-lg font-bold text-gray-700 font-mono">
              {summary?.unique_courses || 0}
            </span>
            <span className="text-xs text-gray-400">branches</span>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Percentile Range</p>
          <div className="flex items-baseline gap-1 mt-1">
            <span className="text-lg font-bold text-emerald-600 font-mono">
              {summary?.min_percentile !== null && summary?.min_percentile !== undefined 
                ? summary.min_percentile.toFixed(2) + '%' 
                : '—'}
            </span>
            <span className="text-gray-400 text-xs mx-1">to</span>
            <span className="text-lg font-bold text-emerald-600 font-mono">
              {summary?.max_percentile !== null && summary?.max_percentile !== undefined 
                ? summary.max_percentile.toFixed(2) + '%' 
                : '—'}
            </span>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Merit Rank Range</p>
          <div className="flex items-baseline gap-1 mt-1 font-mono">
            <span className="text-lg font-bold text-purple-600">
              {summary?.min_merit !== null && summary?.min_merit !== undefined 
                ? `#${summary.min_merit.toLocaleString()}` 
                : '—'}
            </span>
            <span className="text-gray-400 text-xs mx-1 font-sans">to</span>
            <span className="text-lg font-bold text-purple-600">
              {summary?.max_merit !== null && summary?.max_merit !== undefined 
                ? `#${summary.max_merit.toLocaleString()}` 
                : '—'}
            </span>
          </div>
        </div>
      </div>

      {/* Filter Panel */}
      <Card className="p-5 bg-white shadow-sm border border-gray-200">
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-primary-600" />
            <span className="font-semibold text-gray-800 text-sm">Filter Criteria</span>
            {activeFiltersCount > 0 && (
              <span className="bg-primary-100 text-primary-800 text-xs font-semibold px-2 py-0.5 rounded-full">
                {activeFiltersCount} active
              </span>
            )}
          </div>
          <button 
            type="button" 
            onClick={() => setFiltersOpen(!filtersOpen)}
            className="text-gray-400 hover:text-gray-600 p-1"
          >
            {filtersOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>

        {filtersOpen && (
          <div className="space-y-4 pt-4">
            {/* Row 1: Primary Dimensions */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              <Select
                label="Academic Year"
                value={year}
                onChange={(e) => { setYear(e.target.value); setPage(1); }}
                options={[
                  { value: '', label: 'All Years' },
                  ...(filterOptions?.years || [2026]).map((y) => ({ value: String(y), label: `AY ${y}` })),
                ]}
              />

              <Select
                label="CAP Round"
                value={roundNumber}
                onChange={(e) => { setRoundNumber(e.target.value); setPage(1); }}
                options={[
                  { value: '', label: 'All CAP Rounds' },
                  ...(filterOptions?.rounds || [1, 2, 3, 4]).map((r) => ({ value: String(r), label: `CAP Round ${r}` })),
                ]}
              />

              <Input
                label="Search College"
                placeholder="Name or Code (e.g. 01002)..."
                value={collegeSearch}
                onChange={(e) => { setCollegeSearch(e.target.value); setPage(1); }}
              />

              <Input
                label="Search Course"
                placeholder="Branch name or code..."
                value={courseSearch}
                onChange={(e) => { setCourseSearch(e.target.value); setPage(1); }}
              />
            </div>

            {/* Row 2: Category, Gender, District, Seat Section */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              <Select
                label="Seat Category"
                value={categoryCode}
                onChange={(e) => { setCategoryCode(e.target.value); setPage(1); }}
                options={[
                  { value: '', label: 'All Categories' },
                  ...(filterOptions?.categories || []).map((cat) => ({ value: cat, label: cat })),
                ]}
              />

              <Select
                label="Gender"
                value={gender}
                onChange={(e) => { setGender(e.target.value); setPage(1); }}
                options={[
                  { value: '', label: 'All (General & Ladies)' },
                  { value: 'General', label: 'General / Male' },
                  { value: 'Ladies', label: 'Ladies / Female' },
                ]}
              />

              <Input
                label="City / District"
                placeholder="e.g. Amravati, Pune, Mumbai..."
                value={cityDistrict}
                onChange={(e) => { setCityDistrict(e.target.value); setPage(1); }}
              />

              <Select
                label="Seat Section"
                value={seatSection}
                onChange={(e) => { setSeatSection(e.target.value); setPage(1); }}
                options={[
                  { value: '', label: 'All Seat Sections' },
                  { value: 'STATE_LEVEL', label: 'State Level' },
                  { value: 'HOME_UNIVERSITY', label: 'Home University' },
                  { value: 'OTHER_THAN_HOME_UNIVERSITY', label: 'Other Than Home University' },
                ]}
              />
            </div>

            {/* Row 3: Percentile Range, Merit Range & Sort */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 items-end">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Percentile Range</label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    step="0.1"
                    placeholder="Min (0)"
                    value={minPercentile}
                    onChange={(e) => { setMinPercentile(e.target.value); setPage(1); }}
                    className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                  />
                  <span className="text-gray-400 text-xs">to</span>
                  <input
                    type="number"
                    step="0.1"
                    placeholder="Max (100)"
                    value={maxPercentile}
                    onChange={(e) => { setMaxPercentile(e.target.value); setPage(1); }}
                    className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Merit Rank Range</label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    placeholder="Min Rank"
                    value={minMerit}
                    onChange={(e) => { setMinMerit(e.target.value); setPage(1); }}
                    className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                  />
                  <span className="text-gray-400 text-xs">to</span>
                  <input
                    type="number"
                    placeholder="Max Rank"
                    value={maxMerit}
                    onChange={(e) => { setMaxMerit(e.target.value); setPage(1); }}
                    className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
              </div>

              <Select
                label="Sort Order"
                value={sortBy}
                onChange={(e) => { setSortBy(e.target.value); setPage(1); }}
                options={[
                  { value: 'percentile_desc', label: 'Percentile: Highest First' },
                  { value: 'percentile_asc', label: 'Percentile: Lowest First' },
                  { value: 'merit_asc', label: 'Merit Rank: #1 First' },
                  { value: 'merit_desc', label: 'Merit Rank: Highest Rank' },
                  { value: 'college_name', label: 'College Name (A-Z)' },
                  { value: 'course_name', label: 'Course Name (A-Z)' },
                ]}
              />

              {/* Quick Percentile Chips */}
              <div className="space-y-1">
                <span className="block text-xs font-medium text-gray-500">Quick Percentiles</span>
                <div className="flex flex-wrap gap-1">
                  <button
                    type="button"
                    onClick={() => handleQuickPercentile(95, undefined)}
                    className="px-2 py-1 text-xs font-medium rounded bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200"
                  >
                    95%+
                  </button>
                  <button
                    type="button"
                    onClick={() => handleQuickPercentile(90, 95)}
                    className="px-2 py-1 text-xs font-medium rounded bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200"
                  >
                    90-95%
                  </button>
                  <button
                    type="button"
                    onClick={() => handleQuickPercentile(80, 90)}
                    className="px-2 py-1 text-xs font-medium rounded bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200"
                  >
                    80-90%
                  </button>
                  <button
                    type="button"
                    onClick={() => handleQuickPercentile(undefined, undefined)}
                    className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-600 hover:bg-gray-200"
                  >
                    All
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Results Table Card */}
      <Card className="overflow-hidden border border-gray-200 shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50/75 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-gray-900">Extracted Cutoff Results</h2>
            <span className="text-xs bg-gray-200 text-gray-700 px-2 py-0.5 rounded-full font-mono">
              {data?.total.toLocaleString() || 0} matching
            </span>
          </div>

          <div className="text-xs text-gray-500 flex items-center gap-3">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span> ≥95%
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-500"></span> 90-95%
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-purple-500"></span> 80-90%
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-500"></span> &lt;80%
            </span>
          </div>
        </div>

        {isLoading ? (
          <div className="p-16 flex flex-col items-center justify-center gap-3">
            <Spinner className="w-8 h-8 text-primary-600" />
            <p className="text-sm text-gray-500">Querying verified cutoff records...</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-left">
                <thead className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wider font-semibold">
                  <tr>
                    <th className="px-4 py-3 text-right">Merit Rank</th>
                    <th className="px-4 py-3 text-right">Cutoff %ile</th>
                    <th className="px-4 py-3">College</th>
                    <th className="px-4 py-3">Course / Branch</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">Section</th>
                    <th className="px-4 py-3">Stage</th>
                    <th className="px-4 py-3">Round</th>
                    <th className="px-4 py-3 text-center">PDF Provenance</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200 text-sm">
                  {cutoffItems.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="px-6 py-12 text-center text-gray-500">
                        <Building2 className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                        <p className="font-medium text-gray-700">No cutoffs matched your filter criteria.</p>
                        <p className="text-xs text-gray-400 mt-1">Try relaxing filters or resetting to view all allotments.</p>
                      </td>
                    </tr>
                  ) : (
                    cutoffItems.map((item) => (
                      <tr key={item.id} className="hover:bg-blue-50/40 transition-colors">
                        {/* Merit Rank */}
                        <td className="px-4 py-3.5 whitespace-nowrap text-right font-mono font-bold text-gray-900">
                          {item.merit_number !== undefined && item.merit_number !== null
                            ? item.merit_number.toLocaleString()
                            : '—'}
                        </td>

                        {/* Percentile */}
                        <td className="px-4 py-3.5 whitespace-nowrap text-right">
                          <span className={`inline-block px-2.5 py-1 text-xs font-mono font-bold rounded-md border ${getPercentileBadgeClass(item.percentile)}`}>
                            {item.percentile !== undefined && item.percentile !== null
                              ? Number(item.percentile).toFixed(7)
                              : '—'}
                          </span>
                        </td>

                        {/* College */}
                        <td className="px-4 py-3.5 max-w-[280px]">
                          <div className="flex items-start gap-1.5">
                            <span className="font-mono text-xs font-semibold px-1.5 py-0.5 rounded bg-gray-100 text-gray-700 shrink-0 mt-0.5">
                              {item.college_code}
                            </span>
                            <div>
                              <div className="font-medium text-gray-900 leading-snug line-clamp-2" title={item.college_name}>
                                {item.college_name}
                              </div>
                              {(item.district || item.city) && (
                                <div className="text-xs text-gray-400 mt-0.5">
                                  {item.district || item.city}
                                </div>
                              )}
                            </div>
                          </div>
                        </td>

                        {/* Course */}
                        <td className="px-4 py-3.5 max-w-[240px]">
                          <div className="font-medium text-gray-900 leading-snug line-clamp-2" title={item.course_name}>
                            {item.course_name}
                          </div>
                          <span className="text-xs font-mono text-gray-400">
                            {item.course_code}
                          </span>
                        </td>

                        {/* Category & Gender */}
                        <td className="px-4 py-3.5 whitespace-nowrap">
                          <span className="font-semibold text-gray-900 bg-gray-100 px-2 py-0.5 rounded text-xs">
                            {item.category_code}
                          </span>
                          {item.gender && (
                            <span className="block text-[11px] text-gray-500 mt-0.5">
                              {item.gender}
                            </span>
                          )}
                        </td>

                        {/* Section */}
                        <td className="px-4 py-3.5 whitespace-nowrap text-xs text-gray-600">
                          {item.seat_section ? item.seat_section.replace(/_/g, ' ') : '—'}
                        </td>

                        {/* Stage */}
                        <td className="px-4 py-3.5 whitespace-nowrap text-xs text-gray-600 font-mono">
                          {item.stage || 'I'}
                        </td>

                        {/* Round */}
                        <td className="px-4 py-3.5 whitespace-nowrap text-xs text-gray-700 font-medium">
                          <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-semibold text-xs border border-blue-100">
                            Round {item.round_number || 1}
                          </span>
                          <span className="block text-[11px] text-gray-400 mt-0.5">
                            AY {item.year}
                          </span>
                        </td>

                        {/* PDF Provenance */}
                        <td className="px-4 py-3.5 whitespace-nowrap text-center">
                          <span 
                            title={item.source_pdf ? `Extracted by PyMuPDF from: ${item.source_pdf}` : 'Official CAP Round PDF'}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200 cursor-default"
                          >
                            <FileText className="w-3 h-3 text-slate-500" />
                            Page {item.source_page ?? '—'}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {data && data.total > 0 && (
              <div className="border-t border-gray-200 px-6 py-4 bg-white">
                <Pagination
                  page={page}
                  pageSize={pageSize}
                  total={data.total}
                  onPageChange={setPage}
                  onPageSizeChange={(newSize) => {
                    setPageSize(newSize);
                    setPage(1);
                  }}
                />
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}

