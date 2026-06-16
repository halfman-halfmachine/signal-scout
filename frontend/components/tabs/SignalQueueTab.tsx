'use client';

import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import type { QueueView } from '@/lib/types';

const TIER_COLORS: Record<string, string> = {
  IMMEDIATE: '#f87171', ROUTE: '#f97316', DIGEST: '#fbbf24', LOG: '#8888aa',
};

function timeAgo(ts: number): string {
  const sec = Math.floor((Date.now() - ts) / 1000);
  if (sec < 60) return `${sec}s`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h`;
  return `${Math.floor(sec / 86400)}d`;
}

export default function SignalQueueTab({ onGenerate }: { onGenerate: (s: QueueView) => void }) {
  const [signals, setSignals] = useState<QueueView[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDismissed, setShowDismissed] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getSignals({ include_dismissed: showDismissed });
      setSignals(res.signals);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setLoading(false);
    }
  }, [showDismissed]);

  useEffect(() => { load(); }, [load]);

  const handleRoute = async (s: QueueView) => {
    await api.feedback({ signal_id: s.id, was_valuable: true });
    load();
  };

  const handleDismiss = async (s: QueueView) => {
    await api.patchSignal(s.id, { dismissed: true });
    await api.feedback({ signal_id: s.id, was_valuable: false });
    load();
  };

  const handleKeep = async (s: QueueView) => {
    await api.patchSignal(s.id, { kept: true });
    load();
  };

  return (
    <div>
      <div className="flex-between mb-2">
        <h2 style={{ fontSize: 16 }}>Signal Queue</h2>
        <div className="flex">
          <label style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 4 }}>
            <input type="checkbox" checked={showDismissed} onChange={(e) => setShowDismissed(e.target.checked)} style={{ width: 'auto' }} />
            <span className="small">Show dismissed</span>
          </label>
          <button onClick={load}>Refresh</button>
        </div>
      </div>
      {error && <p className="error-text mb-2">{error}</p>}
      {loading ? <div className="dim">Loading...</div> : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {signals.length === 0 && <p className="dim">No signals in queue.</p>}
          {signals.map((s) => (
            <div key={s.id} className="card" style={{ opacity: s.dismissed ? 0.5 : 1 }}>
              <div className="flex-between">
                <div className="flex" style={{ flex: 1, minWidth: 0 }}>
                  <span className="mono" style={{ color: TIER_COLORS[s.tier] || '#888', fontSize: 16, fontWeight: 700, minWidth: 36 }}>{s.score.toFixed(1)}</span>
                  <span className="badge" style={{ background: TIER_COLORS[s.tier] || '#888', color: '#000' }}>{s.tier}</span>
                  <span style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.title}</span>
                </div>
                <div className="flex">
                  <span className="dim small">{s.source || s.platform}</span>
                  <span className="dim small mono">{timeAgo(s.timestamp)}</span>
                </div>
              </div>
              {s.topics.length > 0 && (
                <div className="flex-wrap mt-2">
                  {s.topics.map((t, i) => <span key={i} className="tag">{t}</span>)}
                </div>
              )}
              <div className="flex mt-2" style={{ gap: 6 }}>
                <button onClick={() => handleRoute(s)} style={{ fontSize: 11 }}>Route</button>
                <button onClick={() => handleDismiss(s)} style={{ fontSize: 11 }}>Dismiss</button>
                <button onClick={() => handleKeep(s)} style={{ fontSize: 11 }}>Keep</button>
                <button onClick={() => onGenerate(s)} style={{ fontSize: 11, color: 'var(--accent)' }}>Generate Outputs</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
