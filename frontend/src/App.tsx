import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthLayout } from './layouts/AuthLayout';
import { AdminLayout } from './layouts/AdminLayout';
import { LoginPage } from './pages/LoginPage';
import { CutoffSearchPage } from './pages/CutoffSearchPage';
import { SearchHistoryPage } from './pages/SearchHistoryPage';
import { NotFoundPage } from './pages/NotFoundPage';

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/search" replace />} />
      
      {/* Auth */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
      </Route>

      {/* Admin App */}
      <Route element={<AdminLayout />}>
        <Route path="/search" element={<CutoffSearchPage />} />
        <Route path="/history" element={<SearchHistoryPage />} />

        {/* Redirects from legacy/removed routes directly to Cutoff Search */}
        <Route path="/dashboard" element={<Navigate to="/search" replace />} />
        <Route path="/cutoffs" element={<Navigate to="/search" replace />} />
        <Route path="/analysis/cutoffs" element={<Navigate to="/search" replace />} />
        <Route path="/analysis/round-comparison" element={<Navigate to="/search" replace />} />
        <Route path="/analysis/data-quality" element={<Navigate to="/search" replace />} />
        <Route path="/colleges" element={<Navigate to="/search" replace />} />
        <Route path="/courses" element={<Navigate to="/search" replace />} />
        <Route path="/imports" element={<Navigate to="/search" replace />} />
        <Route path="/imports/*" element={<Navigate to="/search" replace />} />
        <Route path="/parser-errors" element={<Navigate to="/search" replace />} />
        <Route path="/audit-logs" element={<Navigate to="/search" replace />} />
        <Route path="/settings" element={<Navigate to="/search" replace />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};

export default App;
