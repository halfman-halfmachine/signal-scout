'use client';

import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import type { AppSettings, Lens } from '@/lib/types';

export default function LensTab() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const s = await api.getConfig<AppSettings>('app_settings');
      setSettings(s);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      await api.putConfig('app_settings', settings);
      setMsg('Saved');
      setTimeout(() => setMsg(''), 2000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const updateLens = (idx: number, patch: Partial<Lens>) => {
    if (!settings) return;
    const lenses = [...settings.lenses];
    lenses[idx] = { ...lenses[idx], ...patch };
    setSettings({ ...settings, lenses });
  };

  const addLens = () => {
    if (!settings) return;
    const id = `lens_${Date.now()}`;
    setSettings({ ...settings, lenses: [...settings.lenses, { id, name: 'New Lens', weight: 1, active: true, keywords: [] }] });
  };

  const removeLens = (idx: number) => {
    if (!settings) return;
    setSettings({ ...settings, lenses: settings.lenses.filter((_, i) => i !== idx) });
  };

  if (loading) return <div className="dim">Loading...</div>;
  if (!settings) return <div className="error-text">{error}</div>;

  return (
    <div>
      <div className="flex-between mb-2">
        <h2 style={{ fontSize: 16 }}>Lenses / Filters</h2>
        <div className="flex">
          <button onClick={addLens}>+ Add Lens</button>
          <button onClick={save} disabled={saving} className="primary">{saving ? 'Saving...' : 'Save'}</button>
          {msg && <span className="success-text">{msg}</span>}
        </div>
      </div>
      {error && <p className="error-text mb-2">{error}</p>}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {settings.lenses.map((lens, i) => (
          <LensCard key={lens.id} lens={lens} onChange={(patch) => updateLens(i, patch)} onRemove={() => removeLens(i)} />
        ))}
      </div>
    </div>
  );
}

function LensCard({ lens, onChange, onRemove }: { lens: Lens; onChange: (patch: Partial<Lens>) => void; onRemove: () => void }) {
  const [kwInput, setKwInput] = useState('');

  const addKeyword = () => {
    if (kwInput.trim()) {
      onChange({ keywords: [...lens.keywords, kwInput.trim()] });
      setKwInput('');
    }
  };

  return (
    <div className="card">
      <div className="flex-between">
        <div className="flex">
          <input type="checkbox" checked={lens.active} onChange={(e) => onChange({ active: e.target.checked })} style={{ width: 'auto' }} />
          <input value={lens.name} onChange={(e) => onChange({ name: e.target.value })} style={{ width: 180, fontWeight: 600 }} />
          <label style={{ margin: 0 }}>Weight:</label>
          <input type="number" value={lens.weight} onChange={(e) => onChange({ weight: parseFloat(e.target.value) || 0 })} style={{ width: 60 }} step="0.1" min="0" max="5" />
        </div>
        <button onClick={onRemove} style={{ color: 'var(--error)', border: 'none' }}>Remove</button>
      </div>
      <div className="mt-2">
        <div className="flex">
          <input value={kwInput} onChange={(e) => setKwInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addKeyword())} placeholder="Add keyword..." style={{ maxWidth: 200 }} />
          <button onClick={addKeyword} type="button">+</button>
        </div>
        <div className="flex-wrap mt-2">
          {lens.keywords.map((kw, j) => (
            <span key={j} className="tag">{kw}<span className="remove" onClick={() => onChange({ keywords: lens.keywords.filter((_, k) => k !== j) })}>×</span></span>
          ))}
        </div>
      </div>
    </div>
  );
}
