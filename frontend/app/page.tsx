'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { AuthStatus } from '@/lib/types';
import Login from '@/components/Login';
import Dashboard from '@/components/Dashboard';

export default function Home() {
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.authStatus().then(setAuth).catch((e) => setError(e.message));
  }, []);

  if (error) return <div style={{ padding: 40, textAlign: 'center' }}><p className="error-text">{error}</p><p className="dim mt-2">Cannot reach backend. Is the server running?</p></div>;
  if (!auth) return <div style={{ padding: 40, textAlign: 'center' }} className="dim">Loading...</div>;

  if (auth.auth_required && !auth.authenticated) {
    return <Login onSuccess={() => setAuth({ ...auth, authenticated: true })} />;
  }

  return <Dashboard authRequired={auth.auth_required} onLogout={() => setAuth({ ...auth, authenticated: false })} />;
}
