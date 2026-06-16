'use client';

import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import type { AppSettings, Framework } from '@/lib/types';

export default function FrameworksTab() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const [activeId, setActiveId] = useState<string>('');

  const load = useCallback(async () => {
    try {
      const s = await api.getConfig<AppSettings>('app_settings');
      setSettings(s);
      if (s.frameworks.length > 0 && !activeId) setActiveId(s.frameworks[0].id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setLoading(false);
    }
  }, [activeId]);

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

  const addFramework = () => {
    if (!settings) return;
    const fw: Framework = { id: `fw_${Date.now()}`, name: 'New Framework', beats: [''], best: '' };
    setSettings({ ...settings, frameworks: [...settings.frameworks, fw] });
  };

  const updateFramework = (idx: number, patch: Partial<Framework>) => {
    if (!settings) return;
    const fws = [...settings.frameworks];
    fws[idx] = { ...fws[idx], ...patch };
    setSettings({ ...settings, frameworks: fws });
  };

  const removeFramework = (idx: number) => {
    if (!settings) return;
    setSettings({ ...settings, frameworks: settings.frameworks.filter((_, i) => i !== idx) });
  };

  if (loading) return <div className="dim">Loading...</div>;
  if (!settings) return <div className="error-text">{error}</div>;

  return (
    <div>
      <div className="flex-between mb-2">
        <h2 style={{ fontSize: 16 }}>Frameworks</h2>
        <div className="flex">
          <button onClick={addFramework}>+ Add Framework</button>
          <button onClick={save} disabled={saving} className="primary">{saving ? 'Saving...' : 'Save'}</button>
          {msg && <span className="success-text">{msg}</span>}
        </div>
      </div>
      {error && <p className="error-text mb-2">{error}</p>}

      <div className="mb-2">
        <label>Active Framework (used by generation)</label>
        <select value={activeId} onChange={(e) => setActiveId(e.target.value)} style={{ width: 300 }}>
          {settings.frameworks.map((fw) => <option key={fw.id} value={fw.id}>{fw.name}</option>)}
        </select>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {settings.frameworks.map((fw, i) => (
          <div key={fw.id} className="card" style={{ borderColor: fw.id === activeId ? 'var(--accent)' : undefined }}>
            <div className="flex-between">
              <div className="grid-2" style={{ flex: 1, gap: 8 }}>
                <div><label>Name</label><input value={fw.name} onChange={(e) => updateFramework(i, { name: e.target.value })} /></div>
                <div><label>Best for</label><input value={fw.best} onChange={(e) => updateFramework(i, { best: e.target.value })} /></div>
              </div>
              <button onClick={() => removeFramework(i)} style={{ color: 'var(--error)', border: 'none', marginLeft: 8 }}>Remove</button>
            </div>
            <div className="mt-2">
              <label>Beats (one per line)</label>
              <textarea value={fw.beats.join('\n')} onChange={(e) => updateFramework(i, { beats: e.target.value.split('\n') })} rows={3} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
