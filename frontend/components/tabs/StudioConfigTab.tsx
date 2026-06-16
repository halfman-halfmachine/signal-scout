'use client';

import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import type { AppSettings } from '@/lib/types';

export default function StudioConfigTab() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const [customPov, setCustomPov] = useState('');

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

  const toggleInList = (key: keyof AppSettings, item: string) => {
    if (!settings) return;
    const list = settings[key] as string[];
    const newList = list.includes(item) ? list.filter((x) => x !== item) : [...list, item];
    setSettings({ ...settings, [key]: newList });
  };

  if (loading) return <div className="dim">Loading...</div>;
  if (!settings) return <div className="error-text">{error}</div>;

  const showSocial = settings.output_types.includes('social-post');

  return (
    <div>
      <div className="flex-between mb-2">
        <h2 style={{ fontSize: 16 }}>Studio Config</h2>
        <div className="flex">
          <button onClick={save} disabled={saving} className="primary">{saving ? 'Saving...' : 'Save'}</button>
          {msg && <span className="success-text">{msg}</span>}
        </div>
      </div>
      {error && <p className="error-text mb-2">{error}</p>}

      <p className="dim small mb-2">Generation uses the server&apos;s configured key or falls back to templates.</p>

      <div className="grid-2" style={{ gap: 20, alignItems: 'start' }}>
        <div>
          <label>Output Types</label>
          <MultiToggle options={['social-post', 'blog-post', 'newsletter', 'executive-brief', 'talking-points', 'thread']} selected={settings.output_types} onToggle={(v) => toggleInList('output_types', v)} />

          {showSocial && (
            <div className="mt-4">
              <label>Social Platforms</label>
              <MultiToggle options={['twitter', 'linkedin', 'mastodon', 'threads', 'bluesky']} selected={settings.social_platforms} onToggle={(v) => toggleInList('social_platforms', v)} />
            </div>
          )}

          <div className="mt-4">
            <label>Input Modes</label>
            <MultiToggle options={settings.input_modes} selected={settings.input_modes} onToggle={(v) => toggleInList('input_modes', v)} />
          </div>
        </div>

        <div>
          <label>Personas</label>
          <MultiToggle options={settings.personas} selected={settings.personas} onToggle={(v) => toggleInList('personas', v)} />

          <div className="mt-4">
            <label>POV Options</label>
            <MultiToggle options={settings.pov_options} selected={settings.pov_options} onToggle={(v) => toggleInList('pov_options', v)} />
          </div>

          <div className="mt-4">
            <label>Custom POV</label>
            <input value={customPov} onChange={(e) => setCustomPov(e.target.value)} placeholder="Enter custom POV text..." />
          </div>

          <div className="mt-4">
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <input type="checkbox" style={{ width: 'auto' }} defaultChecked />
              Web Research
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}

function MultiToggle({ options, selected, onToggle }: { options: string[]; selected: string[]; onToggle: (v: string) => void }) {
  return (
    <div className="flex-wrap" style={{ gap: 6 }}>
      {options.map((opt) => (
        <button key={opt} onClick={() => onToggle(opt)} style={{ background: selected.includes(opt) ? 'var(--accent)' : undefined, color: selected.includes(opt) ? '#000' : undefined, fontSize: 12 }}>
          {opt}
        </button>
      ))}
    </div>
  );
}
