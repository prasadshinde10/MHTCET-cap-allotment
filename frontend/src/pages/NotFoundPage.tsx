import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Search, ArrowLeft } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-12 h-12 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500 mx-auto mb-4">
          <Search className="h-6 w-6" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight mb-1">Page Not Found</h2>
        <p className="text-xs text-slate-500 mb-6">The requested admissions page or route does not exist.</p>
        <Link to="/search">
          <Button variant="primary" size="md">
            <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />
            Return to Cutoff Search
          </Button>
        </Link>
      </div>
    </div>
  );
};

export default NotFoundPage;
