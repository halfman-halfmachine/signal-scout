'use client';

import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import type { AppSettings, Persona, PovOption, InputMode, OutputType, SocialPlatform } from '@/lib/types';

export default function StudioConfigTab() {
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

  if (loading) return <div className="dim">Loading...</div>;
  if (!settings) return <div className="error-text">{error}</div>;

  // ── Personas ───────────────────────────────────────────────────────────
  const addPersona = () => {
    const p: Persona = { id: `persona_${Date.now()}`, name: 'New Persona', archetype: '', description: '', painPoints: [], tone: '', formatPref: '', platform: '', ctaType: '', custom: true };
    setSettings({ ...settings, personas: [...settings.personas, p] });
  };
  const updatePersona = (i: number, patch: Partial<Persona>) => {
    const arr = [...settings.personas];
    arr[i] = { ...arr[i], ...patch };
    setSettings({ ...settings, personas: arr });
  };
  const removePersona = (i: number) => setSettings({ ...settings, personas: settings.personas.filter((_, j) => j !== i) });

  // ── POV options ────────────────────────────────────────────────────────
  const addPov = () => {
    const p: PovOption = { id: `pov_${Date.now()}`, name: 'New POV', desc: '' };
    setSettings({ ...settings, pov_options: [...settings.pov_options, p] });
  };
  const updatePov = (i: number, patch: Partial<PovOption>) => {
    const arr = [...settings.pov_options];
    arr[i] = { ...arr[i], ...patch };
    setSettings({ ...settings, pov_options: arr });
  };
  const removePov = (i: number) => setSettings({ ...settings, pov_options: settings.pov_options.filter((_, j) => j !== i) });

  // ── Input modes ────────────────────────────────────────────────────────
  const addMode = () => {
    const m: InputMode = { id: `mode_${Date.now()}`, icon: '', name: 'New Input Mode', desc: '' };
    setSettings({ ...settings, input_modes: [...settings.input_modes, m] });
  };
  const updateMode = (i: number, patch: Partial<InputMode>) => {
    const arr = [...settings.input_modes];
    arr[i] = { ...arr[i], ...patch };
    setSettings({ ...settings, input_modes: arr });
  };
  const removeMode = (i: number) => setSettings({ ...settings, input_modes: settings.input_modes.filter((_, j) => j !== i) });

  // ── Output types ───────────────────────────────────────────────────────
  const addOutput = () => {
    const o: OutputType = { id: `out_${Date.now()}`, icon: '', name: 'New Output Type', desc: '' };
    setSettings({ ...settings, output_types: [...settings.output_types, o] });
  };
  const updateOutput = (i: number, patch: Partial<OutputType>) => {
    const arr = [...settings.output_types];
    arr[i] = { ...arr[i], ...patch };
    setSettings({ ...settings, output_types: arr });
  };
  const removeOutput = (i: number) => setSettings({ ...settings, output_types: settings.output_types.filter((_, j) => j !== i) });

  // ── Social platforms ───────────────────────────────────────────────────
  const addPlatform = () => {
    const p: SocialPlatform = { id: `plat_${Date.now()}`, name: 'New Platform' };
    setSettings({ ...settings, social_platforms: [...settings.social_platforms, p] });
  };
  const updatePlatform = (i: number, patch: Partial<SocialPlatform>) => {
    const arr = [...settings.social_platforms];
    arr[i] = { ...arr[i], ...patch };
    setSettings({ ...settings, social_platforms: arr });
  };
  const removePlatform = (i: number) => setSettings({ ...settings, social_platforms: settings.social_platforms.filter((_, j) => j !== i) });

  return (
    <div>
      <div className="flex-between mb-2">
        <div>
          <h2 style={{ fontSize: 16 }}>Studio Config</h2>
          <p className="dim small">Catalogs the Output Studio uses to build generation prompts. Edits change the prompt; the seeded <span className="mono">id</span> drives format-specific logic, so existing ids are locked.</p>
        </div>
        <div className="flex">
          <button onClick={save} disabled={saving} className="primary">{saving ? 'Saving...' : 'Save'}</button>
          {msg && <span className="success-text">{msg}</span>}
        </div>
      </div>
      {error && <p className="error-text mb-2">{error}</p>}

      {/* Personas */}
      <div className="card mt-4">
        <div className="flex-between mb-2">
          <h3 style={{ fontSize: 14 }}>Personas</h3>
          <button onClick={addPersona}>+ Add Persona</button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {settings.personas.map((p, i) => (
            <div key={p.id} className="card">
              <div className="flex-between">
                <div className="grid-2" style={{ flex: 1, gap: 8 }}>
                  <div><label>Name</label><input value={p.name} onChange={(e) => updatePersona(i, { name: e.target.value })} /></div>
                  <div><label>Archetype</label><input value={p.archetype} onChange={(e) => updatePersona(i, { archetype: e.target.value })} /></div>
                </div>
                <button onClick={() => removePersona(i)} style={{ color: 'var(--error)', border: 'none', marginLeft: 8 }}>Remove</button>
              </div>
              <div className="mt-2"><label>Description</label><textarea value={p.description} onChange={(e) => updatePersona(i, { description: e.target.value })} rows={2} /></div>
              <div className="grid-2 mt-2" style={{ gap: 8 }}>
                <div><label>Tone</label><input value={p.tone} onChange={(e) => updatePersona(i, { tone: e.target.value })} /></div>
                <div><label>Format Preference</label><input value={p.formatPref} onChange={(e) => updatePersona(i, { formatPref: e.target.value })} /></div>
                <div><label>Platform</label><input value={p.platform} onChange={(e) => updatePersona(i, { platform: e.target.value })} /></div>
                <div><label>CTA Type</label><input value={p.ctaType} onChange={(e) => updatePersona(i, { ctaType: e.target.value })} /></div>
              </div>
              <StrListEditor label="Pain Points" items={p.painPoints} onChange={(v) => updatePersona(i, { painPoints: v })} />
            </div>
          ))}
          {settings.personas.length === 0 && <p className="dim small">No personas. Add one to target generation.</p>}
        </div>
      </div>

      {/* POV options */}
      <div className="card mt-4">
        <div className="flex-between mb-2">
          <h3 style={{ fontSize: 14 }}>POV Options</h3>
          <button onClick={addPov}>+ Add POV</button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {settings.pov_options.map((p, i) => (
            <div key={p.id} className="flex" style={{ gap: 8, alignItems: 'flex-end' }}>
              <div style={{ width: '25%' }}><label>Name</label><input value={p.name} onChange={(e) => updatePov(i, { name: e.target.value })} /></div>
              <div style={{ flex: 1 }}><label>Description</label><input value={p.desc} onChange={(e) => updatePov(i, { desc: e.target.value })} /></div>
              <button onClick={() => removePov(i)} style={{ color: 'var(--error)', border: 'none' }}>×</button>
            </div>
          ))}
          {settings.pov_options.length === 0 && <p className="dim small">No POV options.</p>}
        </div>
      </div>

      {/* Input modes */}
      <div className="card mt-4">
        <div className="flex-between mb-2">
          <h3 style={{ fontSize: 14 }}>Input Modes</h3>
          <button onClick={addMode}>+ Add Mode</button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {settings.input_modes.map((m, i) => (
            <div key={m.id} className="flex" style={{ gap: 8, alignItems: 'flex-end' }}>
              <div style={{ width: '25%' }}><label>Name</label><input value={m.name} onChange={(e) => updateMode(i, { name: e.target.value })} /></div>
              <div style={{ flex: 1 }}><label>Description</label><input value={m.desc} onChange={(e) => updateMode(i, { desc: e.target.value })} /></div>
              <button onClick={() => removeMode(i)} style={{ color: 'var(--error)', border: 'none' }}>×</button>
            </div>
          ))}
          {settings.input_modes.length === 0 && <p className="dim small">No input modes.</p>}
        </div>
      </div>

      {/* Output types */}
      <div className="card mt-4">
        <div className="flex-between mb-2">
          <h3 style={{ fontSize: 14 }}>Output Types</h3>
          <button onClick={addOutput}>+ Add Output Type</button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {settings.output_types.map((o, i) => (
            <div key={o.id} className="flex" style={{ gap: 8, alignItems: 'flex-end' }}>
              <div style={{ width: '25%' }}><label>Name</label><input value={o.name} onChange={(e) => updateOutput(i, { name: e.target.value })} /></div>
              <div style={{ flex: 1 }}><label>Description</label><input value={o.desc} onChange={(e) => updateOutput(i, { desc: e.target.value })} /></div>
              <button onClick={() => removeOutput(i)} style={{ color: 'var(--error)', border: 'none' }}>×</button>
            </div>
          ))}
          {settings.output_types.length === 0 && <p className="dim small">No output types.</p>}
        </div>
      </div>

      {/* Social platforms */}
      <div className="card mt-4">
        <div className="flex-between mb-2">
          <h3 style={{ fontSize: 14 }}>Social Platforms</h3>
          <button onClick={addPlatform}>+ Add Platform</button>
        </div>
        <div className="flex-wrap" style={{ gap: 8 }}>
          {settings.social_platforms.map((p, i) => (
            <div key={p.id} className="flex" style={{ gap: 4, alignItems: 'center' }}>
              <input value={p.name} onChange={(e) => updatePlatform(i, { name: e.target.value })} style={{ width: 140 }} />
              <button onClick={() => removePlatform(i)} style={{ color: 'var(--error)', border: 'none' }}>×</button>
            </div>
          ))}
          {settings.social_platforms.length === 0 && <p className="dim small">No social platforms.</p>}
        </div>
      </div>
    </div>
  );
}

function StrListEditor({ label, items, onChange }: { label: string; items: string[]; onChange: (v: string[]) => void }) {
  const [input, setInput] = useState('');
  const add = () => { if (input.trim()) { onChange([...items, input.trim()]); setInput(''); } };
  return (
    <div className="mt-2">
      <label>{label}</label>
      <div className="flex" style={{ marginBottom: 6 }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), add())} placeholder={`Add ${label.toLowerCase()}...`} />
        <button onClick={add} type="button">+</button>
      </div>
      <div className="flex-wrap">
        {items.map((item, i) => (
          <span key={i} className="tag">{item}<span className="remove" onClick={() => onChange(items.filter((_, j) => j !== i))}>×</span></span>
        ))}
      </div>
    </div>
  );
}
