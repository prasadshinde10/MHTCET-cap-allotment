import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getRoundComparison } from '../api/analysis';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import Card from '../components/ui/Card';
import StatsCard from '../components/StatsCard';
import Spinner from '../components/ui/Spinner';

export function RoundComparisonPage() {
  const [year, setYear] = useState('2026');
  const [roundA, setRoundA] = useState('1');
  const [roundB, setRoundB] = useState('2');
  const [collegeCode, setCollegeCode] = useState('');
  const [courseCode, setCourseCode] = useState('');

  const { data, refetch, isFetching } = useQuery({
    queryKey: ['round-comparison', year, roundA, roundB, collegeCode, courseCode],
    queryFn: () => getRoundComparison({ 
      year: Number(year), 
      round_a: Number(roundA), 
      round_b: Number(roundB), 
      college_code: collegeCode || undefined, 
      course_code: courseCode || undefined 
    }),
    enabled: false,
  });

  const handleCompare = () => {
    refetch();
  };

  const results = Array.isArray(data) ? data : [];
  
  const increased = results.filter((r: any) => r.percentile_change !== null && r.percentile_change > 0).length;
  const decreased = results.filter((r: any) => r.percentile_change !== null && r.percentile_change < 0).length;
  const unchanged = results.filter((r: any) => r.percentile_change !== null && r.percentile_change === 0).length;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Round Comparison</h1>

      <Card className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4 items-end">
          <Input label="Year" value={year} onChange={(e) => setYear(e.target.value)} type="number" required />
          <Input label="Round A" value={roundA} onChange={(e) => setRoundA(e.target.value)} type="number" required />
          <Input label="Round B" value={roundB} onChange={(e) => setRoundB(e.target.value)} type="number" required />
          <Input label="College Code (Optional)" placeholder="e.g. 01002" value={collegeCode} onChange={(e) => setCollegeCode(e.target.value)} />
          <Button onClick={handleCompare} isLoading={isFetching}>Compare Rounds</Button>
        </div>
      </Card>

      {isFetching && (
        <div className="p-8 flex justify-center"><Spinner /></div>
      )}

      {data && !isFetching && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <StatsCard title="Total Compared" value={results.length.toString()} color="blue" />
            <StatsCard title="Cutoff Increased" value={increased.toString()} color="green" />
            <StatsCard title="Cutoff Decreased" value={decreased.toString()} color="red" />
            <StatsCard title="Unchanged" value={unchanged.toString()} color="gray" />
          </div>

          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Course / College</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Section</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stage</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Round {roundA} %</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Round {roundB} %</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Change</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200 text-sm">
                  {results.length === 0 ? (
                    <tr><td colSpan={7} className="px-6 py-8 text-center text-sm text-gray-500">No matching cutoff records found across both rounds to compare.</td></tr>
                  ) : (
                    results.map((row: any, i: number) => {
                      const diff = row.percentile_change;
                      const diffColor = diff > 0 ? 'text-green-600 font-semibold' : diff < 0 ? 'text-red-600 font-semibold' : 'text-gray-500';
                      return (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-gray-900">
                            <div className="font-medium">{row.course_name} ({row.course_code})</div>
                            <div className="text-xs text-gray-500">{row.college_name}</div>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap font-medium text-gray-900">{row.category_code}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-gray-500">{row.seat_section}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-gray-500">{row.stage}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-gray-700">
                            {row.round_a_percentile !== null && row.round_a_percentile !== undefined ? Number(row.round_a_percentile).toFixed(7) : '-'}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-gray-700">
                            {row.round_b_percentile !== null && row.round_b_percentile !== undefined ? Number(row.round_b_percentile).toFixed(7) : '-'}
                          </td>
                          <td className={`px-4 py-3 whitespace-nowrap text-right font-mono ${diffColor}`}>
                            {diff !== null && diff !== undefined ? `${diff > 0 ? '+' : ''}${Number(diff).toFixed(7)}` : '-'}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
