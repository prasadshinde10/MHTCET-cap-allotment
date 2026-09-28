import React, { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import { ShieldCheck, AlertCircle } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // If already authenticated, redirect to search
  if (isAuthenticated) {
    return <Navigate to="/search" replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await login({ username, password });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid username or password');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <div className="mb-5 text-center">
        <h3 className="text-base font-bold text-slate-900 tracking-tight">Admin Sign In</h3>
        <p className="text-xs text-slate-500 mt-0.5">Enter your credentials to manage admissions</p>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200/80 rounded-lg p-3 mb-4 flex items-center gap-2 text-rose-700 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-500" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Username"
          type="text"
          required
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="admin"
          autoComplete="username"
        />
        <Input
          label="Password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
          autoComplete="current-password"
        />
        <div className="pt-1">
          <Button
            type="submit"
            size="md"
            className="w-full"
            isLoading={isLoading}
            disabled={isLoading || !username || !password}
          >
            <ShieldCheck className="w-4 h-4 mr-1.5" />
            Sign in to Portal
          </Button>
        </div>
      </form>
    </div>
  );
};

export default LoginPage;
