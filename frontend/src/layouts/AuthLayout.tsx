import React from 'react';
import { Outlet } from 'react-router-dom';
import { GraduationCap } from 'lucide-react';

export const AuthLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-11 h-11 rounded-xl bg-blue-600 mx-auto flex items-center justify-center text-white shadow-md shadow-blue-500/20 mb-3.5">
          <GraduationCap className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-bold text-white tracking-tight">
          CAP Admissions Portal
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Counselling & Cutoff Verification System
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-sm px-4">
        <div className="bg-white py-6 px-6 shadow-xl rounded-2xl border border-slate-200">
          <Outlet />
        </div>
      </div>
    </div>
  );
};

export default AuthLayout;
