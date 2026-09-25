import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { AlertCircle } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <AlertCircle className="mx-auto h-16 w-16 text-primary-500 mb-4" />
        <h2 className="text-3xl font-extrabold text-gray-900 mb-2">404 - Not Found</h2>
        <p className="text-gray-500 mb-8">The page you are looking for does not exist.</p>
        <Link to="/dashboard">
          <Button variant="primary" size="lg">
            Return to Dashboard
          </Button>
        </Link>
      </div>
    </div>
  );
};
