'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

export default function Login({ onSuccess }: { onSuccess: () => void }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await api.login(password);
      if (res.ok) onSuccess();
      else setError(res.error || 'Login failed');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
      <form onSubmit={handleSubmit} className="card" style={{ width: 320 }}>
        <h2 style={{ marginBottom: 16, fontSize: 18 }}>Signal Scout</h2>
        <label>Password</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoFocus />
        {error && <p className="error-text mt-2">{error}</p>}
        <button type="submit" className="primary mt-4" style={{ width: '100%' }} disabled={loading}>
          {loading ? 'Signing in...' : 'Sign In'}
        </button>
      </form>
    </div>
  );
}
