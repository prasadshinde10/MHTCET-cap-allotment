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
      setError(err.response?.data?.detail || 'Invalid administrator username or password');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <div className="mb-5 text-center">
        <h3 className="text-base font-bold text-[#172B4D] tracking-tight">Admin Authentication</h3>
        <p className="text-xs text-[#5B6B7F] mt-0.5">Authorized access to admissions and allotment data</p>
      </div>

      {error && (
        <div className="bg-[#FDF2F2] border border-[#F8B4B4] rounded-lg p-3 mb-4 flex items-center gap-2 text-[#C53030] text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0 text-[#C53030]" />
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
            className="w-full bg-[#123B66] hover:bg-[#0B2545] text-white"
            isLoading={isLoading}
            disabled={isLoading || !username || !password}
          >
            <ShieldCheck className="w-4 h-4 mr-1.5" />
            Sign in to Console
          </Button>
        </div>
      </form>
    </div>
  );
};

export default LoginPage;
