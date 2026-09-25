import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthLayout } from './layouts/AuthLayout';
import { AdminLayout } from './layouts/AdminLayout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { NotFoundPage } from './pages/NotFoundPage';

import { ImportNewPage } from './pages/ImportNewPage';
import { ImportHistoryPage } from './pages/ImportHistoryPage';
import { ImportDetailPage } from './pages/ImportDetailPage';

import { CollegesPage } from './pages/CollegesPage';
import { CoursesPage } from './pages/CoursesPage';
import { CutoffsPage } from './pages/CutoffsPage';
import { RoundComparisonPage } from './pages/RoundComparisonPage';
import { DataQualityPage } from './pages/DataQualityPage';
import { ParserErrorsPage } from './pages/ParserErrorsPage';
import { AuditLogsPage } from './pages/AuditLogsPage';
import { SettingsPage } from './pages/SettingsPage';

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
      </Route>

      <Route element={<AdminLayout />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/colleges" element={<CollegesPage />} />
        <Route path="/courses" element={<CoursesPage />} />
        <Route path="/cutoffs" element={<CutoffsPage />} />
        <Route path="/analysis/cutoffs" element={<CutoffsPage />} />
        <Route path="/imports/new" element={<ImportNewPage />} />
        <Route path="/imports" element={<ImportHistoryPage />} />
        <Route path="/imports/:id" element={<ImportDetailPage />} />
        <Route path="/parser-errors" element={<ParserErrorsPage />} />
        <Route path="/analysis/round-comparison" element={<RoundComparisonPage />} />
        <Route path="/analysis/data-quality" element={<DataQualityPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/audit-logs" element={<AuditLogsPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};

export default App;
