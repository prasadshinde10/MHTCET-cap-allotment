import { useQuery } from '@tanstack/react-query';
import { getDataQuality } from '../api/analysis';
import Card from '../components/ui/Card';
import StatsCard from '../components/StatsCard';
import Spinner from '../components/ui/Spinner';

export function DataQualityPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['data-quality'],
    queryFn: getDataQuality,
  });

  if (isLoading) return <div className="p-8 flex justify-center"><Spinner /></div>;
  if (!data) return <div className="p-8 text-center text-red-500">Failed to load data quality metrics</div>;

  const categoryEntries = Object.entries(data.category_distribution || {});
  const sectionEntries = Object.entries(data.section_distribution || {});

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Data Quality Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <StatsCard title="Total Records" value={data.total_records?.toString() || '0'} color="blue" />
        <StatsCard title="Missing Merit No" value={data.records_with_missing_merit?.toString() || '0'} color="yellow" />
        <StatsCard title="Missing Percentile" value={data.records_with_missing_percentile?.toString() || '0'} color="red" />
        <StatsCard title="Zero Merit" value={data.records_with_zero_merit?.toString() || '0'} color="purple" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="Category Distribution">
          {categoryEntries.length === 0 ? (
            <p className="text-sm text-gray-500 py-4 text-center">No categories found.</p>
          ) : (
            <ul className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
              {categoryEntries.map(([category, count]) => (
                <li key={category} className="py-2.5 flex justify-between items-center text-sm">
                  <span className="font-semibold text-gray-900">{category}</span>
                  <span className="bg-gray-100 px-2.5 py-0.5 rounded-full font-mono text-gray-700">{String(count)} records</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Seat Section Distribution">
          {sectionEntries.length === 0 ? (
            <p className="text-sm text-gray-500 py-4 text-center">No sections found.</p>
          ) : (
            <ul className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
              {sectionEntries.map(([section, count]) => (
                <li key={section} className="py-2.5 flex justify-between items-center text-sm">
                  <span className="font-semibold text-gray-900">{section}</span>
                  <span className="bg-gray-100 px-2.5 py-0.5 rounded-full font-mono text-gray-700">{String(count)} records</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
