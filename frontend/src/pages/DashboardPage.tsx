import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Building2, BookOpen, Database, AlertTriangle,
  CheckCircle, XCircle, AlertCircle, Upload, Search,
  GitCompare, ArrowRight, ShieldCheck, FileText
} from 'lucide-react';
import { dashboardApi } from '../api/dashboard';
import { StatsCard } from '../components/StatsCard';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Spinner } from '../components/ui/Spinner';
import { formatDate, formatNumber } from '../utils/formatters';

export const DashboardPage: React.FC = () => {
  const { data: stats, isLoading, isError } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: dashboardApi.getDashboardStats,
    refetchInterval: 30000,
  });

  const getStatusBadgeVariant = (status: string): 'success' | 'error' | 'info' | 'warning' | 'default' => {
    switch (status.toLowerCase()) {
      case 'completed':
      case 'resolved':
        return 'success';
      case 'failed':
      case 'error':
      case 'critical':
        return 'error';
      case 'processing':
      case 'pending':
      case 'open':
        return 'info';
      case 'completed_with_warnings':
      case 'warning':
        return 'warning';
      default:
        return 'default';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px]">
        <Spinner className="w-8 h-8 text-primary-600" />
      </div>
    );
  }

  if (isError || !stats) {
    return (
      <div className="bg-red-50 p-6 rounded-lg border border-red-200 text-red-700">
        <h3 className="font-semibold mb-1">Error Loading Dashboard</h3>
        <p className="text-sm">Unable to fetch dashboard statistics. Please verify the backend service is running.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Hero Welcome Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-indigo-950 text-white rounded-2xl p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" /> PyMuPDF Page-by-Page Extraction
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-white/10 text-gray-300">
                Source of Truth: PDF
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              CAP Cutoff Intelligence Portal
            </h1>
            <p className="text-gray-300 text-sm mt-1.5 max-w-2xl">
              Upload official MHT-CET CAP Round PDFs, extract allotment cutoffs with zero hallucination, and perform multi-dimensional cutoff analysis.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              to="/cutoffs"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm bg-primary-600 hover:bg-primary-500 text-white shadow transition-colors"
            >
              <Search className="w-4 h-4" /> Analyze Cutoffs
            </Link>
            <Link
              to="/imports/new"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm bg-white/10 hover:bg-white/20 text-white border border-white/20 transition-colors"
            >
              <Upload className="w-4 h-4" /> Upload CAP PDF
            </Link>
          </div>
        </div>
      </div>

      {/* Top Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatsCard
          label="Total Extracted Cutoffs"
          value={formatNumber(stats.total_cutoffs)}
          icon={Database}
          iconColor="text-primary-600"
          iconBg="bg-primary-50"
          subtitle="From official CAP PDFs"
        />
        <StatsCard
          label="Colleges Extracted"
          value={formatNumber(stats.total_colleges)}
          icon={Building2}
          iconColor="text-blue-600"
          iconBg="bg-blue-50"
          subtitle="Parsed automatically"
        />
        <StatsCard
          label="Courses & Branches"
          value={formatNumber(stats.total_courses)}
          icon={BookOpen}
          iconColor="text-emerald-600"
          iconBg="bg-emerald-50"
          subtitle="Engineering disciplines"
        />
        <StatsCard
          label="Parser Extraction Logs"
          value={formatNumber(stats.open_parser_errors)}
          icon={AlertTriangle}
          iconColor={stats.open_parser_errors > 0 ? "text-amber-600" : "text-emerald-600"}
          iconBg={stats.open_parser_errors > 0 ? "bg-amber-50" : "bg-emerald-50"}
          subtitle={stats.open_parser_errors > 0 ? "Flagged lines for audit" : "100% clean parsing"}
        />
      </div>

      {/* Quick Action Navigation Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Link
          to="/cutoffs"
          className="group p-5 bg-white rounded-xl border border-gray-200 hover:border-primary-300 hover:shadow-md transition-all flex flex-col justify-between"
        >
          <div>
            <div className="w-10 h-10 rounded-lg bg-primary-50 text-primary-600 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
              <Search className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-gray-900 text-base group-hover:text-primary-600 transition-colors">
              Cutoff Analysis Engine
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              Filter cutoffs by Percentile, Merit Rank, College, Course, Gender, Category, and District.
            </p>
          </div>
          <div className="flex items-center text-xs font-semibold text-primary-600 mt-4">
            Launch Analysis <ArrowRight className="w-3.5 h-3.5 ml-1 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        <Link
          to="/analysis/round-comparison"
          className="group p-5 bg-white rounded-xl border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all flex flex-col justify-between"
        >
          <div>
            <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
              <GitCompare className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-gray-900 text-base group-hover:text-blue-600 transition-colors">
              Round-to-Round Comparison
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              Compare cutoff score inflation or drops across CAP Round 1, 2, 3, and 4.
            </p>
          </div>
          <div className="flex items-center text-xs font-semibold text-blue-600 mt-4">
            Compare Rounds <ArrowRight className="w-3.5 h-3.5 ml-1 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        <Link
          to="/imports/new"
          className="group p-5 bg-white rounded-xl border border-gray-200 hover:border-emerald-300 hover:shadow-md transition-all flex flex-col justify-between"
        >
          <div>
            <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
              <Upload className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-gray-900 text-base group-hover:text-emerald-600 transition-colors">
              Import New CAP PDF
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              Upload raw PDF; PyMuPDF processes page-by-page and commits verified records to database.
            </p>
          </div>
          <div className="flex items-center text-xs font-semibold text-emerald-600 mt-4">
            Upload PDF <ArrowRight className="w-3.5 h-3.5 ml-1 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>
      </div>

      {/* CAP Rounds & Imports Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="CAP Round Allotment Records">
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: 'CAP Round I', value: stats.cap_round_1_records, badge: 'Round 1' },
              { label: 'CAP Round II', value: stats.cap_round_2_records, badge: 'Round 2' },
              { label: 'CAP Round III', value: stats.cap_round_3_records, badge: 'Round 3' },
              { label: 'CAP Round IV', value: stats.cap_round_4_records, badge: 'Round 4' },
            ].map((round) => (
              <div key={round.label} className="bg-gray-50 p-4 rounded-xl border border-gray-100 flex flex-col justify-between">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-500 font-semibold">{round.label}</span>
                  <span className="text-[11px] font-medium bg-gray-200 text-gray-700 px-2 py-0.5 rounded">
                    {round.badge}
                  </span>
                </div>
                <p className="text-2xl font-extrabold mt-2 text-gray-900 font-mono">
                  {formatNumber(round.value)}
                  <span className="text-xs text-gray-400 font-normal ml-1">cutoffs</span>
                </p>
              </div>
            ))}
          </div>
        </Card>

        <Card title="PDF Import Pipeline Status">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center p-4 bg-gray-50 rounded-xl border border-gray-100">
              <Database className="w-8 h-8 text-gray-400 mr-4 flex-shrink-0" />
              <div>
                <p className="text-xs text-gray-500 font-semibold">Total Batches</p>
                <p className="text-xl font-bold mt-1 text-gray-900 font-mono">{formatNumber(stats.total_imports)}</p>
              </div>
            </div>
            <div className="flex items-center p-4 bg-emerald-50 rounded-xl border border-emerald-100">
              <CheckCircle className="w-8 h-8 text-emerald-500 mr-4 flex-shrink-0" />
              <div>
                <p className="text-xs text-emerald-700 font-semibold">Fully Completed</p>
                <p className="text-xl font-bold mt-1 text-emerald-900 font-mono">{formatNumber(stats.successful_imports)}</p>
              </div>
            </div>
            <div className="flex items-center p-4 bg-amber-50 rounded-xl border border-amber-100">
              <AlertCircle className="w-8 h-8 text-amber-500 mr-4 flex-shrink-0" />
              <div>
                <p className="text-xs text-amber-700 font-semibold">With Warnings</p>
                <p className="text-xl font-bold mt-1 text-amber-900 font-mono">{formatNumber(stats.warning_imports)}</p>
              </div>
            </div>
            <div className="flex items-center p-4 bg-red-50 rounded-xl border border-red-100">
              <XCircle className="w-8 h-8 text-red-500 mr-4 flex-shrink-0" />
              <div>
                <p className="text-xs text-red-700 font-semibold">Failed Batches</p>
                <p className="text-xl font-bold mt-1 text-red-900 font-mono">{formatNumber(stats.failed_imports)}</p>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Tables Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Recent PDF Imports" padding={false}>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">File</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Round / Year</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Records</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {stats.recent_imports.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-8 text-center text-sm text-gray-500">
                      No imports yet. Upload a CAP cutoff PDF to get started.
                    </td>
                  </tr>
                ) : (
                  stats.recent_imports.map((item, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm font-medium text-gray-900 max-w-[200px] truncate" title={item.filename}>
                        <div className="flex items-center gap-1.5">
                          <FileText className="w-4 h-4 text-gray-400 shrink-0" />
                          <span className="truncate">{item.filename}</span>
                        </div>
                        {item.date && (
                          <div className="text-xs text-gray-400 font-normal mt-0.5">{formatDate(item.date)}</div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        {item.round_name} ({item.year})
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <Badge variant={getStatusBadgeVariant(item.status)}>{item.status}</Badge>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right font-mono font-medium">
                        {formatNumber(item.records)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div className="bg-gray-50 px-4 py-3 border-t border-gray-200 text-right sm:px-6">
            <Link to="/imports" className="text-sm font-medium text-primary-600 hover:text-primary-500">
              View all import history &rarr;
            </Link>
          </div>
        </Card>

        <Card title="Recent Parser Anomaly Logs" padding={false}>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Anomaly Description</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Severity</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Page</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {stats.recent_errors.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-8 text-center text-sm text-gray-500">
                      No parser anomalies. All lines matched cleanly!
                    </td>
                  </tr>
                ) : (
                  stats.recent_errors.map((error, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm text-gray-900 max-w-[250px] truncate" title={error.error}>
                        {error.error}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <Badge variant={getStatusBadgeVariant(error.severity)}>{error.severity}</Badge>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <Badge variant={getStatusBadgeVariant(error.status)}>{error.status}</Badge>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 text-right font-mono">
                        {error.page !== null && error.page !== undefined ? `Page ${error.page}` : '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div className="bg-gray-50 px-4 py-3 border-t border-gray-200 text-right sm:px-6">
            <Link to="/parser-errors" className="text-sm font-medium text-primary-600 hover:text-primary-500">
              View all parser logs &rarr;
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
};

