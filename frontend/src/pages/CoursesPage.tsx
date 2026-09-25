import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getCourses } from '../api/courses';
import { BookOpen, ExternalLink, CheckCircle2 } from 'lucide-react';
import Input from '../components/ui/Input';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Spinner from '../components/ui/Spinner';
import Pagination from '../components/ui/Pagination';

export function CoursesPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [search, setSearch] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['courses', page, pageSize, search],
    queryFn: () => getCourses({ page, page_size: pageSize, search }),
  });

  const courseItems = data?.items || [];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Courses & Branches</h1>
            <Badge variant="success" className="gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> PDF Extracted
            </Badge>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Engineering degree branches parsed from CAP Round allotment tables. PDF is the sole source of truth.
          </p>
        </div>

        <Link
          to="/cutoffs"
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium rounded-lg bg-primary-50 text-primary-700 hover:bg-primary-100 border border-primary-200 transition-colors"
        >
          <BookOpen className="w-4 h-4" /> Open Cutoff Analysis &rarr;
        </Link>
      </div>

      {/* Search Bar */}
      <Card className="p-4 bg-white shadow-sm border border-gray-200">
        <div className="w-full md:w-1/2">
          <Input
            label="Search Courses"
            placeholder="Search by branch name, course code (e.g. 0100219110), or college..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
      </Card>

      {/* Directory Table */}
      <Card className="overflow-hidden border border-gray-200 shadow-sm">
        {isLoading ? (
          <div className="p-16 flex flex-col items-center justify-center gap-3">
            <Spinner className="w-8 h-8 text-primary-600" />
            <p className="text-sm text-gray-500">Loading courses...</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wider font-semibold">
                  <tr>
                    <th className="px-6 py-3 text-left">Course Code</th>
                    <th className="px-6 py-3 text-left">Branch / Degree Course</th>
                    <th className="px-6 py-3 text-left">Institute</th>
                    <th className="px-6 py-3 text-center">Extracted Cutoffs</th>
                    <th className="px-6 py-3 text-right">Cutoff Analysis</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200 text-sm">
                  {courseItems.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                        <BookOpen className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                        <p className="font-medium text-gray-700">No courses found matching your search.</p>
                      </td>
                    </tr>
                  ) : (
                    courseItems.map((course) => (
                      <tr key={course.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap font-mono font-bold text-gray-900">
                          {course.course_code}
                        </td>
                        <td className="px-6 py-4 font-medium text-gray-900">
                          {course.course_name}
                        </td>
                        <td className="px-6 py-4 text-gray-600 max-w-[280px]">
                          {course.college_name ? (
                            <div>
                              <div className="truncate font-medium text-gray-800" title={course.college_name}>
                                {course.college_name}
                              </div>
                              <div className="text-xs text-gray-400 font-mono">
                                College Code: {course.college_code}
                              </div>
                            </div>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                            {course.cutoff_count || 0} records
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right">
                          <Link
                            to={`/cutoffs`}
                            className="inline-flex items-center gap-1 text-xs font-semibold text-primary-600 hover:text-primary-800 bg-primary-50 px-2.5 py-1 rounded border border-primary-200 hover:bg-primary-100 transition-colors"
                          >
                            View Cutoffs <ExternalLink className="w-3 h-3" />
                          </Link>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

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

