import React from 'react';
import { Outlet } from 'react-router-dom';
import { GraduationCap } from 'lucide-react';

export const AuthLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#0B2545] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-12 h-12 rounded-xl bg-[#123B66] border border-[#1769D2]/30 mx-auto flex items-center justify-center text-[#ADCFFF] shadow-md mb-4">
          <GraduationCap className="w-6 h-6 text-[#80B3FF]" />
        </div>
        <h2 className="text-xl font-bold text-white tracking-tight">
          Central Admissions Portal
        </h2>
        <p className="text-xs text-[#8292A2] mt-1">
          Counselling, Cutoff Verification & Seat Allotment Console
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-sm px-4">
        <div className="bg-white py-6 px-6 shadow-elevated rounded-xl border border-[#D9E2EC]">
          <Outlet />
        </div>
      </div>
    </div>
  );
};

export default AuthLayout;
