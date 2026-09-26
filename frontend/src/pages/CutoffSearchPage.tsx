import React, { useState, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getCutoffs, Cutoff } from '../api/cutoffs';
import { getFilterOptions } from '../api/analysis';
import { 
  Search, RotateCcw, Building2, BookOpen, MapPin, 
  Sparkles, Download, LayoutGrid, Table as TableIcon,
  HelpCircle, AlertCircle, ArrowUpDown
} from 'lucide-react';
import SearchableSelect, { SearchableOption } from '../components/ui/SearchableSelect';
import Select from '../components/ui/Select';
import Button from '../components/ui/Button';
import FilterChips, { ActiveFilter } from '../components/ui/FilterChips';
import Badge from '../components/ui/Badge';
import Spinner from '../components/ui/Spinner';
import { saveSearchHistory, SearchHistoryFilters } from '../utils/searchHistory';
import toast from 'react-hot-toast';

// Grouped cutoff row across rounds 1 to 4
interface GroupedCutoffRow {
  key: string;
  collegeCode: string;
  collegeName: string;
  district: string;
  collegeType: string;
  courseCode: string;
  courseName: string;
  categoryCode: string;
  seatSection: string;
  gender?: string;
  stage: string;
  rounds: {
    1: { percentile?: number; meritNumber?: number } | null;
    2: { percentile?: number; meritNumber?: number } | null;
    3: { percentile?: number; meritNumber?: number } | null;
    4: { percentile?: number; meritNumber?: number } | null;
  };
}

const CASTE_CATEGORIES = [
  { value: '', label: 'All Categories' },
  { value: 'OPEN', label: 'OPEN (Open / General Merit)' },
  { value: 'OBC', label: 'OBC (Other Backward Class)' },
  { value: 'SC', label: 'SC (Scheduled Caste)' },
  { value: 'ST', label: 'ST (Scheduled Tribe)' },
  { value: 'VJ', label: 'VJ / DT (Vimukta Jati / Denotified Tribe)' },
  { value: 'NT1', label: 'NT-1 / NT-B (Nomadic Tribe 1)' },
  { value: 'NT2', label: 'NT-2 / NT-C (Nomadic Tribe 2)' },
  { value: 'NT3', label: 'NT-3 / NT-D (Nomadic Tribe 3)' },
  { value: 'SEBC', label: 'SEBC (Socially & Educationally Backward Class)' },
];

const RESERVATION_TYPES = [
  { value: '', label: 'General / No Special Reservation' },
  { value: 'TFWS', label: 'TFWS (Tuition Fee Waiver Scheme)' },
  { value: 'EWS', label: 'EWS (Economically Weaker Section)' },
  { value: 'DEF', label: 'Defence Quota (DEF)' },
  { value: 'PWD', label: 'PWD (Persons with Disabilities)' },
  { value: 'ORPHAN', label: 'Orphan Quota' },
  { value: 'MI', label: 'Minority Quota' },
];

const COLLEGE_TYPES = [
  { value: '', label: 'All College Types' },
  { value: 'Autonomous', label: 'Autonomous' },
  { value: 'Non-Autonomous', label: 'Non-Autonomous' },
];

const GENDER_OPTIONS = [
  { value: '', label: 'All Seats (Open to All)' },
  { value: 'ladies', label: 'Ladies Only (Female Reserved Seats)' },
];

const ROUND_OPTIONS = [
  { value: '', label: 'All Rounds (Rounds I – IV)' },
  { value: '1', label: 'CAP Round I Only' },
  { value: '2', label: 'CAP Round II Only' },
  { value: '3', label: 'CAP Round III Only' },
  { value: '4', label: 'CAP Round IV Only' },
];

export const CutoffSearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Form Filter States
  const [selectedCourse, setSelectedCourse] = useState<string>(searchParams.get('course') || '');
  const [collegeType, setCollegeType] = useState<string>(searchParams.get('collegeType') || '');
  const [casteCategory, setCasteCategory] = useState<string>(searchParams.get('category') || '');
  const [reservationType, setReservationType] = useState<string>(searchParams.get('reservation') || '');
  const [gender, setGender] = useState<string>(searchParams.get('gender') || '');
  const [district, setDistrict] = useState<string>(searchParams.get('district') || '');
  const [capYear, setCapYear] = useState<string>(searchParams.get('year') || '2026');
  const [capRound, setCapRound] = useState<string>(searchParams.get('round') || '');
  const [studentPercentile, setStudentPercentile] = useState<string>(searchParams.get('percentile') || '');

  // UI Control States
  const [hasSearched, setHasSearched] = useState(false);
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');
  const [tableFilter, setTableFilter] = useState('');
  const [sortBy, setSortBy] = useState<'percentile_desc' | 'percentile_asc' | 'college' | 'course'>('percentile_desc');

  // Synchronize state when URL query parameters change (e.g. from Search History navigation)
  useEffect(() => {
    const courseParam = searchParams.get('course');
    const typeParam = searchParams.get('collegeType');
    const catParam = searchParams.get('category');
    const resParam = searchParams.get('reservation');
    const genParam = searchParams.get('gender');
    const distParam = searchParams.get('district');
    const yearParam = searchParams.get('year');
    const roundParam = searchParams.get('round');
    const pctParam = searchParams.get('percentile');

    const hasAnyParam = Boolean(
      courseParam || typeParam || catParam || resParam || genParam || distParam || yearParam || roundParam || pctParam
    );

    if (hasAnyParam) {
      if (courseParam !== null) setSelectedCourse(courseParam);
      if (typeParam !== null) setCollegeType(typeParam);
      if (catParam !== null) setCasteCategory(catParam);
      if (resParam !== null) setReservationType(resParam);
      if (genParam !== null) setGender(genParam);
      if (distParam !== null) setDistrict(distParam);
      if (yearParam !== null) setCapYear(yearParam);
      if (roundParam !== null) setCapRound(roundParam);
      if (pctParam !== null) setStudentPercentile(pctParam);
      setHasSearched(true);
    }
  }, [searchParams]);

  // Load dynamic filter options (courses, years, rounds, districts) from API
  const { data: filterOptions, isLoading: isFilterOptionsLoading } = useQuery({
    queryKey: ['filterOptions'],
    queryFn: getFilterOptions,
    staleTime: 300000,
  });

  // Auto-set capYear to the latest year available in database if not set by URL query
  useEffect(() => {
    if (filterOptions?.years?.length && !searchParams.get('year')) {
      setCapYear(filterOptions.years[0].toString());
    }
  }, [filterOptions, searchParams]);

  // College metadata lookup map: code -> details (uses filterOptions which returns ALL colleges)
  const collegeMetaMap = useMemo(() => {
    const map = new Map<string, { type: string; district?: string; city?: string }>();
    if (filterOptions?.colleges) {
      for (const col of filterOptions.colleges) {
        map.set(col.college_code, {
          type: col.college_type || 'Non-Autonomous',
          district: col.district || undefined,
          city: col.city || undefined,
        });
      }
    }
    return map;
  }, [filterOptions]);

  // Build searchable course options
  const courseOptions: SearchableOption[] = useMemo(() => {
    const list: SearchableOption[] = [{ value: '', label: 'All Branches / Any' }];
    if (filterOptions?.courses) {
      // De-duplicate by course_name
      const seen = new Set<string>();
      filterOptions.courses.forEach((c) => {
        if (!seen.has(c.course_name)) {
          seen.add(c.course_name);
          list.push({
            value: c.course_name,
            label: c.course_name,
            sublabel: `Code: ${c.course_code}`,
          });
        }
      });
    }
    return list;
  }, [filterOptions]);

  // Build searchable district options with unified historical names
  const districtOptions: SearchableOption[] = useMemo(() => {
    return [
      { value: '', label: 'All Districts' },
      { value: 'Ahmednagar', label: 'Ahmednagar (Ahilyanagar)' },
      { value: 'Akola', label: 'Akola' },
      { value: 'Amravati', label: 'Amravati' },
      { 
        value: 'Chhatrapati Sambhajinagar', 
        label: 'Chhatrapati Sambhajinagar (Aurangabad)', 
        sublabel: 'Same city • All colleges from Aurangabad & Sambhajinagar' 
      },
      { value: 'Bhandara', label: 'Bhandara' },
      { value: 'Buldhana', label: 'Buldhana' },
      { value: 'Chandrapur', label: 'Chandrapur' },
      { 
        value: 'Dharashiv', 
        label: 'Dharashiv (Osmanabad)', 
        sublabel: 'Same district • All colleges from Osmanabad & Dharashiv' 
      },
      { value: 'Dhule', label: 'Dhule' },
      { value: 'Gadchiroli', label: 'Gadchiroli' },
      { value: 'Gondia', label: 'Gondia' },
      { value: 'Hingoli', label: 'Hingoli' },
      { value: 'Jalgaon', label: 'Jalgaon' },
      { value: 'Jalna', label: 'Jalna' },
      { value: 'Kolhapur', label: 'Kolhapur' },
      { value: 'Latur', label: 'Latur' },
      { value: 'Mumbai', label: 'Mumbai City' },
      { value: 'Mumbai Suburban', label: 'Mumbai Suburban' },
      { value: 'Nagpur', label: 'Nagpur' },
      { value: 'Nanded', label: 'Nanded' },
      { value: 'Nandurbar', label: 'Nandurbar' },
      { value: 'Nashik', label: 'Nashik' },
      { value: 'Palghar', label: 'Palghar' },
      { value: 'Parbhani', label: 'Parbhani' },
      { value: 'Pune', label: 'Pune' },
      { value: 'Raigad', label: 'Raigad' },
      { value: 'Ratnagiri', label: 'Ratnagiri' },
      { value: 'Sangli', label: 'Sangli' },
      { value: 'Satara', label: 'Satara' },
      { value: 'Sindhudurg', label: 'Sindhudurg' },
      { value: 'Solapur', label: 'Solapur' },
      { value: 'Thane', label: 'Thane' },
      { value: 'Wardha', label: 'Wardha' },
      { value: 'Washim', label: 'Washim' },
      { value: 'Yavatmal', label: 'Yavatmal' },
    ];
  }, []);

  // Available Years
  const yearOptions = useMemo(() => {
    if (filterOptions?.years && filterOptions.years.length > 0) {
      return filterOptions.years.map((y) => ({ value: y.toString(), label: y.toString() }));
    }
    return [{ value: '2026', label: '2026' }];
  }, [filterOptions]);

  // Determine computed category query parameter
  const computedCategoryQuery = useMemo(() => {
    if (reservationType === 'TFWS') return 'TFWS';
    if (reservationType === 'EWS') return 'EWS';
    if (reservationType === 'DEF') {
      return casteCategory ? `DEF${casteCategory}` : 'DEF';
    }
    if (reservationType === 'PWD') {
      return casteCategory ? `PWD${casteCategory}` : 'PWD';
    }
    if (reservationType === 'ORPHAN') return 'ORPHAN';
    if (reservationType === 'MI') return 'MI';
    return casteCategory || undefined;
  }, [reservationType, casteCategory]);

  // Computed district query parameter ensuring Sambhajinagar/Aurangabad and Dharashiv/Osmanabad match all colleges
  const computedDistrictQuery = useMemo(() => {
    if (!district) return undefined;
    const lower = district.toLowerCase();
    if (lower.includes('sambhajinagar') || lower.includes('aurangabad')) {
      return 'Sambhajinagar';
    }
    if (lower.includes('dharashiv') || lower.includes('osmanabad')) {
      return 'Dharashiv';
    }
    return district;
  }, [district]);

  // Helper to format district name with historical alias
  const formatDistrictDisplay = (dist: string) => {
    if (!dist) return 'Maharashtra';
    const lower = dist.toLowerCase();
    if (lower.includes('sambhajinagar') || lower.includes('aurangabad')) {
      return 'Chhatrapati Sambhajinagar (Aurangabad)';
    }
    if (lower.includes('dharashiv') || lower.includes('osmanabad')) {
      return 'Dharashiv (Osmanabad)';
    }
    return dist;
  };

  // Query Cutoffs
  // Determine which rounds to query
  const roundsToQuery = useMemo(() => {
    if (capRound) return [Number(capRound)];
    return [1, 2, 3, 4];
  }, [capRound]);

  // Build common query params (shared across all round queries)
  const commonQueryParams = useMemo(() => ({
    page: 1,
    page_size: 500,
    year: capYear ? Number(capYear) : undefined,
    course: selectedCourse || undefined,
    category_code: computedCategoryQuery,
    gender: gender || undefined,
    city_district: computedDistrictQuery,
    max_percentile: studentPercentile ? Number(studentPercentile) : undefined,
    is_deleted: false as const,
  }), [capYear, selectedCourse, computedCategoryQuery, gender, computedDistrictQuery, studentPercentile]);

  // Fetch Round 1
  const { data: round1Data, isLoading: r1Loading, isError: r1Error, error: r1Err, refetch: r1Refetch } = useQuery({
    queryKey: ['cutoffsR1', commonQueryParams],
    queryFn: () => getCutoffs({ ...commonQueryParams, round_number: 1 }),
    enabled: hasSearched && roundsToQuery.includes(1),
  });

  // Fetch Round 2
  const { data: round2Data, isLoading: r2Loading, isError: r2Error, error: r2Err, refetch: r2Refetch } = useQuery({
    queryKey: ['cutoffsR2', commonQueryParams],
    queryFn: () => getCutoffs({ ...commonQueryParams, round_number: 2 }),
    enabled: hasSearched && roundsToQuery.includes(2),
  });

  // Fetch Round 3
  const { data: round3Data, isLoading: r3Loading, isError: r3Error, error: r3Err, refetch: r3Refetch } = useQuery({
    queryKey: ['cutoffsR3', commonQueryParams],
    queryFn: () => getCutoffs({ ...commonQueryParams, round_number: 3 }),
    enabled: hasSearched && roundsToQuery.includes(3),
  });

  // Fetch Round 4
  const { data: round4Data, isLoading: r4Loading, isError: r4Error, error: r4Err, refetch: r4Refetch } = useQuery({
    queryKey: ['cutoffsR4', commonQueryParams],
    queryFn: () => getCutoffs({ ...commonQueryParams, round_number: 4 }),
    enabled: hasSearched && roundsToQuery.includes(4),
  });

  // Combined loading / error state
  const isSearching = r1Loading || r2Loading || r3Loading || r4Loading;
  const isError = r1Error || r2Error || r3Error || r4Error;
  const error = r1Err || r2Err || r3Err || r4Err;
  const refetch = () => { r1Refetch(); r2Refetch(); r3Refetch(); r4Refetch(); };

  // Total counts info for display
  const totalInfo = useMemo(() => {
    const r1Total = round1Data?.total ?? 0;
    const r2Total = round2Data?.total ?? 0;
    const r3Total = round3Data?.total ?? 0;
    const r4Total = round4Data?.total ?? 0;
    return {
      total: r1Total + r2Total + r3Total + r4Total,
      r1Truncated: r1Total > 500,
      r2Truncated: r2Total > 500,
      r3Truncated: r3Total > 500,
      r4Truncated: r4Total > 500,
      anyTruncated: r1Total > 500 || r2Total > 500 || r3Total > 500 || r4Total > 500,
    };
  }, [round1Data, round2Data, round3Data, round4Data]);

  // Group cutoffs from ALL rounds by College + Course + Category + Seat Section
  const groupedRows: GroupedCutoffRow[] = useMemo(() => {
    const map = new Map<string, GroupedCutoffRow>();

    // Helper: process items from a specific round
    const processItems = (items: Cutoff[] | undefined, roundNum: 1 | 2 | 3 | 4) => {
      if (!items) return;
      items.forEach((item: Cutoff) => {
        // Determine college type
        const colMeta = item.college_code ? collegeMetaMap.get(item.college_code) : undefined;
        let effectiveType = colMeta?.type || 'Non-Autonomous';
        if (item.college_name?.toLowerCase().includes('autonomous')) {
          effectiveType = 'Autonomous';
        }

        // Filter by college type if specified
        if (collegeType) {
          if (collegeType === 'Autonomous' && !effectiveType.toLowerCase().includes('autonomous')) {
            return;
          }
          if (collegeType === 'Non-Autonomous' && effectiveType.toLowerCase().includes('autonomous')) {
            return;
          }
        }

        const collegeCode = item.college_code || 'N/A';
        const courseCode = item.course_code || 'N/A';
        const categoryCode = item.category_code || 'N/A';
        const seatSection = item.seat_section || 'STATE_LEVEL';
        const stage = item.stage || 'I';

        const key = `${collegeCode}_${courseCode}_${categoryCode}_${seatSection}_${stage}`;

        if (!map.has(key)) {
          map.set(key, {
            key,
            collegeCode,
            collegeName: item.college_name || 'Unknown College',
            district: formatDistrictDisplay(item.district || item.city || colMeta?.district || colMeta?.city || 'Maharashtra'),
            collegeType: effectiveType,
            courseCode,
            courseName: item.course_name || 'Engineering Course',
            categoryCode,
            seatSection,
            gender: item.gender,
            stage,
            rounds: {
              1: null,
              2: null,
              3: null,
              4: null,
            },
          });
        }

        const row = map.get(key)!;
        row.rounds[roundNum] = {
          percentile: item.percentile !== undefined && item.percentile !== null ? Number(item.percentile) : undefined,
          meritNumber: item.merit_number !== undefined && item.merit_number !== null ? Number(item.merit_number) : undefined,
        };
      });
    };

    // Process all round data
    processItems(round1Data?.items, 1);
    processItems(round2Data?.items, 2);
    processItems(round3Data?.items, 3);
    processItems(round4Data?.items, 4);

    const rows = Array.from(map.values());

    // Sort rows
    return rows.sort((a, b) => {
      if (sortBy === 'college') {
        return a.collegeName.localeCompare(b.collegeName);
      }
      if (sortBy === 'course') {
        return a.courseName.localeCompare(b.courseName);
      }
      
      // By percentile (best round 1 or earliest available round)
      const pA = a.rounds[1]?.percentile ?? a.rounds[2]?.percentile ?? a.rounds[3]?.percentile ?? a.rounds[4]?.percentile ?? -1;
      const pB = b.rounds[1]?.percentile ?? b.rounds[2]?.percentile ?? b.rounds[3]?.percentile ?? b.rounds[4]?.percentile ?? -1;

      if (sortBy === 'percentile_asc') {
        return pA - pB;
      }
      // percentile_desc
      return pB - pA;
    });
  }, [round1Data, round2Data, round3Data, round4Data, collegeMetaMap, collegeType, sortBy]);

  // Filter grouped rows by quick search input
  const filteredGroupedRows = useMemo(() => {
    if (!tableFilter.trim()) return groupedRows;
    const q = tableFilter.toLowerCase();
    return groupedRows.filter(
      (r) =>
        r.collegeName.toLowerCase().includes(q) ||
        r.collegeCode.toLowerCase().includes(q) ||
        r.courseName.toLowerCase().includes(q) ||
        r.categoryCode.toLowerCase().includes(q) ||
        r.district.toLowerCase().includes(q)
    );
  }, [groupedRows, tableFilter]);

  // Handle Find Colleges
  const handleFindColleges = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setHasSearched(true);
    refetch();

    // Save to Search History
    const currentFilters: SearchHistoryFilters = {
      course: selectedCourse,
      collegeType,
      category: casteCategory,
      reservation: reservationType,
      gender,
      district,
      year: capYear,
      round: capRound,
      percentile: studentPercentile,
    };

    saveSearchHistory(currentFilters, groupedRows.length);
    toast.success('Search executed', { duration: 2000 });
  };

  // Handle Reset Filters
  const handleResetFilters = () => {
    setSelectedCourse('');
    setCollegeType('');
    setCasteCategory('');
    setReservationType('');
    setGender('');
    setDistrict('');
    setCapYear(filterOptions?.years?.[0]?.toString() || '2026');
    setCapRound('');
    setStudentPercentile('');
    setTableFilter('');
    setSearchParams({});
    toast.success('Filters reset to default');
  };

  // Build active filter chips
  const activeChips: ActiveFilter[] = useMemo(() => {
    const chips: ActiveFilter[] = [];
    if (selectedCourse) {
      chips.push({ id: 'course', label: 'Branch', value: selectedCourse });
    }
    if (collegeType) {
      chips.push({ id: 'collegeType', label: 'Type', value: collegeType });
    }
    if (casteCategory) {
      const found = CASTE_CATEGORIES.find((c) => c.value === casteCategory);
      chips.push({ id: 'category', label: 'Caste', value: found ? found.label.split(' ')[0] : casteCategory });
    }
    if (reservationType) {
      const found = RESERVATION_TYPES.find((r) => r.value === reservationType);
      chips.push({ id: 'reservation', label: 'Reservation', value: found ? found.label.split(' ')[0] : reservationType });
    }
    if (gender === 'ladies') {
      chips.push({ id: 'gender', label: 'Quota', value: 'Ladies Only' });
    }
    if (district) {
      const found = districtOptions.find((d) => d.value === district);
      chips.push({ id: 'district', label: 'District', value: found ? found.label : district });
    }
    if (capRound) {
      chips.push({ id: 'round', label: 'CAP Round', value: `Round ${capRound}` });
    }
    if (studentPercentile) {
      chips.push({ id: 'percentile', label: 'Score', value: `≤ ${Number(studentPercentile).toFixed(4)}%` });
    }
    return chips;
  }, [selectedCourse, collegeType, casteCategory, reservationType, gender, district, capRound, studentPercentile]);

  const handleRemoveChip = (id: string) => {
    switch (id) {
      case 'course':
        setSelectedCourse('');
        break;
      case 'collegeType':
        setCollegeType('');
        break;
      case 'category':
        setCasteCategory('');
        break;
      case 'reservation':
        setReservationType('');
        break;
      case 'gender':
        setGender('');
        break;
      case 'district':
        setDistrict('');
        break;
      case 'round':
        setCapRound('');
        break;
      case 'percentile':
        setStudentPercentile('');
        break;
    }
  };

  // Export to CSV
  const handleExportCSV = () => {
    if (filteredGroupedRows.length === 0) {
      toast.error('No results to export');
      return;
    }

    const headers = [
      'College Code',
      'College Name',
      'District',
      'College Type',
      'Course Code',
      'Course Name',
      'Category',
      'Seat Section',
      'Round 1 Cutoff %',
      'Round 1 Merit',
      'Round 2 Cutoff %',
      'Round 2 Merit',
      'Round 3 Cutoff %',
      'Round 3 Merit',
      'Round 4 Cutoff %',
      'Round 4 Merit',
    ];

    const rows = filteredGroupedRows.map((r) => [
      `"${r.collegeCode}"`,
      `"${r.collegeName.replace(/"/g, '""')}"`,
      `"${r.district}"`,
      `"${r.collegeType}"`,
      `"${r.courseCode}"`,
      `"${r.courseName.replace(/"/g, '""')}"`,
      `"${r.categoryCode}"`,
      `"${r.seatSection}"`,
      r.rounds[1]?.percentile !== undefined ? r.rounds[1]?.percentile : 'N/A',
      r.rounds[1]?.meritNumber !== undefined ? r.rounds[1]?.meritNumber : 'N/A',
      r.rounds[2]?.percentile !== undefined ? r.rounds[2]?.percentile : 'N/A',
      r.rounds[2]?.meritNumber !== undefined ? r.rounds[2]?.meritNumber : 'N/A',
      r.rounds[3]?.percentile !== undefined ? r.rounds[3]?.percentile : 'N/A',
      r.rounds[3]?.meritNumber !== undefined ? r.rounds[3]?.meritNumber : 'N/A',
      r.rounds[4]?.percentile !== undefined ? r.rounds[4]?.percentile : 'N/A',
      r.rounds[4]?.meritNumber !== undefined ? r.rounds[4]?.meritNumber : 'N/A',
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `mhtcet_cutoffs_${capYear}_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('Cutoff comparison exported to CSV');
  };

  // Format round cell
  const renderRoundCell = (roundData: { percentile?: number; meritNumber?: number } | null) => {
    if (!roundData || (roundData.percentile === undefined && roundData.meritNumber === undefined)) {
      return (
        <span className="inline-block px-2 py-0.5 text-xs font-mono font-medium text-gray-400 bg-gray-50 border border-gray-100 rounded">
          N/A
        </span>
      );
    }

    const studentScore = studentPercentile ? Number(studentPercentile) : null;
    const isEligible = studentScore !== null && roundData.percentile !== undefined && roundData.percentile <= studentScore;
    const margin = isEligible && roundData.percentile !== undefined ? (studentScore - roundData.percentile).toFixed(2) : null;

    return (
      <div className="flex flex-col items-end">
        <div className="flex items-center gap-1">
          {isEligible && (
            <span className="inline-flex items-center text-[10px] font-bold text-emerald-600 bg-emerald-50 px-1 rounded" title={`Eligible: Student score is ${margin}% above cutoff`}>
              ✓
            </span>
          )}
          <span className={`font-mono font-semibold text-sm ${isEligible ? 'text-emerald-700 font-bold' : 'text-gray-900'}`}>
            {roundData.percentile !== undefined ? `${roundData.percentile.toFixed(4)}%` : 'N/A'}
          </span>
        </div>
        {roundData.meritNumber !== undefined && (
          <span className="text-[11px] font-mono text-gray-500">
            Merit #{roundData.meritNumber.toLocaleString()}
          </span>
        )}
      </div>
    );
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-gray-900 tracking-tight">Cutoff Search</h1>
              <Badge variant="info" className="uppercase text-[10px] tracking-wider font-semibold">
                Admin Counselling
              </Badge>
            </div>
            <p className="text-sm text-gray-500 mt-1">
              Select student preferences below to evaluate cutoff percentiles and merit ranks across CAP Rounds 1–4.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleResetFilters}
              className="flex items-center gap-1.5 text-gray-600 hover:text-gray-900"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset Filters
            </Button>
          </div>
        </div>
      </div>

      {/* STEP 1: Student Preference Form */}
      <form onSubmit={handleFindColleges} className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <div className="px-5 py-4 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary-600 text-white text-xs font-bold">
              1
            </span>
            <h2 className="text-sm font-bold text-gray-800 uppercase tracking-wider">
              Student Preference Form
            </h2>
          </div>
          <span className="text-xs text-gray-500">Fill answers given by candidate</span>
        </div>

        <div className="p-5 space-y-6">
          {/* Section A: Academic Preference */}
          <div>
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-primary-600" />
              Academic & Course Preference
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Branch / Course */}
              <div>
                <SearchableSelect
                  label="Preferred Branch / Course"
                  placeholder="Select branch..."
                  options={courseOptions}
                  value={selectedCourse}
                  onChange={setSelectedCourse}
                  helperText={selectedCourse ? `Selected: ${selectedCourse}` : 'Leave as "All Branches" for all'}
                />
              </div>

              {/* Student's MHT-CET Percentile Score */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Student's MHT-CET Percentile
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.0000001"
                    min="0"
                    max="100"
                    placeholder="e.g. 85.1234567"
                    value={studentPercentile}
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val === '' || (Number(val) >= 0 && Number(val) <= 100)) {
                        setStudentPercentile(val);
                      }
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 placeholder-gray-400"
                  />
                  {studentPercentile && (
                    <button
                      type="button"
                      onClick={() => setStudentPercentile('')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs"
                      title="Clear score"
                    >
                      ✕
                    </button>
                  )}
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  {studentPercentile
                    ? `Shows colleges with cutoff ≤ ${Number(studentPercentile).toFixed(4)}%`
                    : 'Enter score to see recommended colleges'}
                </p>
              </div>

              {/* CAP Year */}
              <div>
                <Select
                  label="CAP Admission Year"
                  value={capYear}
                  onChange={(e) => setCapYear(e.target.value)}
                  options={yearOptions}
                />
              </div>
            </div>
          </div>

          <div className="border-t border-gray-100" />

          {/* Section B: Student Reservation & Caste */}
          <div>
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-primary-600" />
              Category & Reservation Quota
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {/* Caste Category */}
              <div>
                <Select
                  label="Caste Category"
                  value={casteCategory}
                  onChange={(e) => setCasteCategory(e.target.value)}
                  options={CASTE_CATEGORIES}
                />
              </div>

              {/* Reservation Type */}
              <div>
                <Select
                  label="Reservation Type"
                  value={reservationType}
                  onChange={(e) => setReservationType(e.target.value)}
                  options={RESERVATION_TYPES}
                />
              </div>

              {/* Gender */}
              <div>
                <Select
                  label="Gender / Quota"
                  value={gender}
                  onChange={(e) => setGender(e.target.value)}
                  options={GENDER_OPTIONS}
                />
              </div>
            </div>
          </div>

          <div className="border-t border-gray-100" />

          {/* Section C: College & Location Preferences */}
          <div>
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-primary-600" />
              College Type & Location
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {/* College Type */}
              <div>
                <Select
                  label="College Type"
                  value={collegeType}
                  onChange={(e) => setCollegeType(e.target.value)}
                  options={COLLEGE_TYPES}
                />
              </div>

              {/* District */}
              <div>
                <SearchableSelect
                  label="District"
                  placeholder="Select district..."
                  options={districtOptions}
                  value={district}
                  onChange={setDistrict}
                  helperText="Searchable Maharashtra district list"
                />
              </div>

              {/* Optional CAP Round */}
              <div>
                <Select
                  label="CAP Round Filter (Optional)"
                  value={capRound}
                  onChange={(e) => setCapRound(e.target.value)}
                  options={ROUND_OPTIONS}
                />
              </div>
            </div>
          </div>

          {/* Active Chips Bar */}
          <FilterChips
            filters={activeChips}
            onRemove={handleRemoveChip}
            onClearAll={handleResetFilters}
          />
        </div>

        {/* Form Footer Action */}
        <div className="px-5 py-4 bg-gray-50 border-t border-gray-200 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="text-xs text-gray-500">
            {activeChips.length > 0
              ? `${activeChips.length} filter${activeChips.length > 1 ? 's' : ''} configured`
              : 'Showing all colleges & courses by default'}
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <Button
              type="submit"
              size="lg"
              className="w-full sm:w-auto px-8 bg-primary-600 hover:bg-primary-700 text-white font-semibold flex items-center justify-center gap-2 shadow-md hover:shadow-lg transition-all"
              isLoading={isSearching}
            >
              <Search className="w-4 h-4" />
              Find Colleges
            </Button>
          </div>
        </div>
      </form>

      {/* STEP 2: Matching College Results */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary-600 text-white text-xs font-bold">
              2
            </span>
            <h2 className="text-base font-bold text-gray-900 tracking-tight">
              {studentPercentile ? 'Recommended Colleges' : 'Matching College Results'}
            </h2>
            {hasSearched && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                {filteredGroupedRows.length} {studentPercentile ? 'recommended' : 'matching'} offering{filteredGroupedRows.length === 1 ? '' : 's'}
              </span>
            )}
            {hasSearched && studentPercentile && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                Score: {Number(studentPercentile).toFixed(2)}% (Cutoff ≤ Score)
              </span>
            )}
          </div>

          {/* Controls: Quick filter, Table/Card toggle, CSV Export */}
          {hasSearched && filteredGroupedRows.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              {/* Quick in-table search */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter results..."
                  value={tableFilter}
                  onChange={(e) => setTableFilter(e.target.value)}
                  className="pl-8 pr-3 py-1.5 text-xs bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary-500 w-40 sm:w-52"
                />
              </div>

              {/* Sort by dropdown */}
              <div className="flex items-center text-xs text-gray-500 border border-gray-300 rounded-lg bg-white px-2 py-1">
                <ArrowUpDown className="w-3 h-3 mr-1 text-gray-400" />
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="bg-transparent text-xs text-gray-700 focus:outline-none"
                >
                  <option value="percentile_desc">Cutoff: High to Low</option>
                  <option value="percentile_asc">Cutoff: Low to High</option>
                  <option value="college">College Name</option>
                  <option value="course">Course Name</option>
                </select>
              </div>

              {/* Table / Card view toggle */}
              <div className="flex items-center border border-gray-300 rounded-lg bg-white p-0.5">
                <button
                  type="button"
                  onClick={() => setViewMode('table')}
                  className={`p-1 rounded ${viewMode === 'table' ? 'bg-primary-50 text-primary-700' : 'text-gray-400 hover:text-gray-700'}`}
                  title="Table layout"
                >
                  <TableIcon className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('cards')}
                  className={`p-1 rounded ${viewMode === 'cards' ? 'bg-primary-50 text-primary-700' : 'text-gray-400 hover:text-gray-700'}`}
                  title="Card layout"
                >
                  <LayoutGrid className="w-4 h-4" />
                </button>
              </div>

              {/* Export button */}
              <Button
                variant="outline"
                size="sm"
                onClick={handleExportCSV}
                className="flex items-center gap-1.5 text-xs"
              >
                <Download className="w-3.5 h-3.5" />
                Export CSV
              </Button>
            </div>
          )}
        </div>

        {/* State 1: Before Searching Initial Prompt */}
        {!hasSearched && (
          <div className="bg-white border border-dashed border-gray-300 rounded-xl p-12 text-center shadow-sm">
            <div className="w-12 h-12 rounded-full bg-blue-50 text-primary-600 flex items-center justify-center mx-auto mb-4">
              <Search className="w-6 h-6" />
            </div>
            <h3 className="text-base font-semibold text-gray-800">Ready for Candidate Consultation</h3>
            <p className="text-sm text-gray-500 max-w-md mx-auto mt-1 mb-6">
              Configure student preferences in the form above and click <strong>Find Colleges</strong> to evaluate cutoffs across Round 1, Round 2, Round 3, and Round 4.
            </p>
            <Button
              onClick={() => handleFindColleges()}
              className="bg-primary-600 hover:bg-primary-700 text-white"
            >
              <Search className="w-4 h-4 mr-2" />
              Find Colleges Now
            </Button>
          </div>
        )}

        {/* State 2: Loading State */}
        {hasSearched && isSearching && (
          <div className="bg-white border border-gray-200 rounded-xl p-12 text-center shadow-sm">
            <Spinner className="w-8 h-8 text-primary-600 mx-auto mb-3" />
            <h4 className="text-sm font-semibold text-gray-800">Searching Admissions Cutoff Database</h4>
            <p className="text-xs text-gray-500 mt-1">Retrieving matching colleges and round-wise percentiles...</p>
          </div>
        )}

        {/* State 3: Error State */}
        {hasSearched && !isSearching && isError && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-800 flex items-start gap-4 shadow-sm">
            <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-bold">Failed to load cutoff data</h4>
              <p className="text-xs text-red-600 mt-1">
                {(error as Error)?.message || 'An unexpected error occurred while querying cutoff records. Please ensure backend service is active.'}
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetch()}
                className="mt-3 bg-white text-red-700 border-red-300 hover:bg-red-50"
              >
                Retry Search
              </Button>
            </div>
          </div>
        )}

        {/* State 4: Empty Results */}
        {hasSearched && !isSearching && !isError && filteredGroupedRows.length === 0 && (
          <div className="bg-white border border-gray-200 rounded-xl p-10 text-center shadow-sm">
            <div className="w-12 h-12 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center mx-auto mb-3">
              <HelpCircle className="w-6 h-6" />
            </div>
            <h3 className="text-base font-semibold text-gray-800">No Matching Colleges Found</h3>
            <p className="text-xs text-gray-500 max-w-md mx-auto mt-1 mb-5">
              No college courses in the database matched the selected branch, category, and district combination.
            </p>
            <div className="flex items-center justify-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetFilters}
              >
                Reset All Filters
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  setSelectedCourse('');
                  setDistrict('');
                  handleFindColleges();
                }}
                className="bg-primary-600 text-white"
              >
                Broaden Search (All Branches & Districts)
              </Button>
            </div>
          </div>
        )}

        {/* State 5: Table View Results */}
        {hasSearched && !isSearching && !isError && filteredGroupedRows.length > 0 && viewMode === 'table' && (
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50/75">
                  <tr>
                    <th scope="col" className="px-4 py-3.5 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider w-1/3">
                      College
                    </th>
                    <th scope="col" className="px-4 py-3.5 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider w-1/4">
                      Course
                    </th>
                    <th scope="col" className="px-4 py-3.5 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Category / Quota
                    </th>
                    <th scope="col" className="px-4 py-3.5 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider bg-blue-50/40">
                      Round 1
                    </th>
                    <th scope="col" className="px-4 py-3.5 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Round 2
                    </th>
                    <th scope="col" className="px-4 py-3.5 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Round 3
                    </th>
                    <th scope="col" className="px-4 py-3.5 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Round 4
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white text-sm">
                  {filteredGroupedRows.map((row) => (
                    <tr key={row.key} className="hover:bg-gray-50/80 transition-colors">
                      {/* College Column */}
                      <td className="px-4 py-3.5 align-top">
                        <div className="font-semibold text-gray-900 leading-snug">
                          {row.collegeName}
                        </div>
                        <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                          <span className="font-mono text-xs text-gray-600 bg-gray-100 px-1.5 py-0.5 rounded">
                            {row.collegeCode}
                          </span>
                          <span className="inline-flex items-center text-xs text-gray-500">
                            <MapPin className="w-3 h-3 mr-0.5 text-gray-400" />
                            {row.district}
                          </span>
                          <span className={`inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium rounded ${
                            row.collegeType.toLowerCase().includes('autonomous')
                              ? 'bg-purple-100 text-purple-800'
                              : 'bg-gray-100 text-gray-700'
                          }`}>
                            {row.collegeType}
                          </span>
                        </div>
                      </td>

                      {/* Course Column */}
                      <td className="px-4 py-3.5 align-top">
                        <div className="font-medium text-gray-900 leading-snug">
                          {row.courseName}
                        </div>
                        <div className="font-mono text-[11px] text-gray-400 mt-1">
                          Code: {row.courseCode}
                        </div>
                      </td>

                      {/* Category & Quota */}
                      <td className="px-4 py-3.5 align-top">
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono font-bold text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-900">
                            {row.categoryCode}
                          </span>
                        </div>
                        <div className="text-[11px] text-gray-500 mt-1 flex flex-col gap-0.5">
                          <span>
                            Quota: {row.seatSection.replace(/_/g, ' ')}
                          </span>
                          {row.gender && (
                            <span className="capitalize text-gray-400">
                              Gender: {row.gender}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Round 1 */}
                      <td className="px-4 py-3.5 align-top text-right bg-blue-50/20">
                        {renderRoundCell(row.rounds[1])}
                      </td>

                      {/* Round 2 */}
                      <td className="px-4 py-3.5 align-top text-right">
                        {renderRoundCell(row.rounds[2])}
                      </td>

                      {/* Round 3 */}
                      <td className="px-4 py-3.5 align-top text-right">
                        {renderRoundCell(row.rounds[3])}
                      </td>

                      {/* Round 4 */}
                      <td className="px-4 py-3.5 align-top text-right">
                        {renderRoundCell(row.rounds[4])}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* State 6: Cards View Results */}
        {hasSearched && !isSearching && !isError && filteredGroupedRows.length > 0 && viewMode === 'cards' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredGroupedRows.map((row) => (
              <div
                key={row.key}
                className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm hover:border-primary-300 transition-all flex flex-col justify-between"
              >
                <div>
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-blue-100 text-blue-900">
                      {row.categoryCode}
                    </span>
                    <span className={`text-[10px] font-medium px-2 py-0.5 rounded ${
                      row.collegeType.toLowerCase().includes('autonomous')
                        ? 'bg-purple-100 text-purple-800'
                        : 'bg-gray-100 text-gray-700'
                    }`}>
                      {row.collegeType}
                    </span>
                  </div>

                  <h3 className="font-bold text-gray-900 text-base leading-snug">
                    {row.collegeName}
                  </h3>

                  <div className="flex items-center gap-2 text-xs text-gray-500 mt-1 mb-3">
                    <span className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">
                      {row.collegeCode}
                    </span>
                    <span>•</span>
                    <span className="flex items-center">
                      <MapPin className="w-3 h-3 mr-0.5 text-gray-400" />
                      {row.district}
                    </span>
                  </div>

                  <div className="p-3 bg-gray-50 rounded-lg border border-gray-100 mb-4">
                    <div className="text-xs text-gray-500 font-semibold uppercase tracking-wider mb-0.5">
                      Course / Branch
                    </div>
                    <div className="font-medium text-gray-900 text-sm">
                      {row.courseName}
                    </div>
                    <div className="text-[11px] font-mono text-gray-400 mt-0.5">
                      Choice Code: {row.courseCode}
                    </div>
                  </div>
                </div>

                {/* 4-Round Grid */}
                <div className="pt-3 border-t border-gray-100">
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    Round-wise Cutoffs
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-center">
                    <div className="p-2 bg-blue-50/50 rounded-lg border border-blue-100">
                      <div className="text-[10px] font-bold text-blue-900 uppercase">Round 1</div>
                      <div className="mt-1">{renderRoundCell(row.rounds[1])}</div>
                    </div>
                    <div className="p-2 bg-gray-50 rounded-lg border border-gray-100">
                      <div className="text-[10px] font-bold text-gray-600 uppercase">Round 2</div>
                      <div className="mt-1">{renderRoundCell(row.rounds[2])}</div>
                    </div>
                    <div className="p-2 bg-gray-50 rounded-lg border border-gray-100">
                      <div className="text-[10px] font-bold text-gray-600 uppercase">Round 3</div>
                      <div className="mt-1">{renderRoundCell(row.rounds[3])}</div>
                    </div>
                    <div className="p-2 bg-gray-50 rounded-lg border border-gray-100">
                      <div className="text-[10px] font-bold text-gray-600 uppercase">Round 4</div>
                      <div className="mt-1">{renderRoundCell(row.rounds[4])}</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Results Info & Truncation Warning */}
        {hasSearched && !isSearching && !isError && filteredGroupedRows.length > 0 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white border border-gray-200 rounded-xl px-5 py-3.5 shadow-sm">
            <div className="text-xs text-gray-500">
              Showing <span className="font-semibold text-gray-800">{filteredGroupedRows.length}</span> grouped offerings from{' '}
              <span className="font-semibold text-gray-800">{totalInfo.total.toLocaleString()}</span> total cutoff records
            </div>
            {totalInfo.anyTruncated && (
              <div className="flex items-center gap-1.5 text-xs text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-lg">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                <span>Some results are truncated. Use more specific filters (branch, category, district) to see all data.</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CutoffSearchPage;
