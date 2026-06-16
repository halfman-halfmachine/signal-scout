'use client';

import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import type { EngineConfig } from '@/lib/types';

export default function EngineTab() {
  const [config, setConfig] = useState<EngineConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const c = await api.getConfig<EngineConfig>('engine');
      setConfig(c);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await api.putConfig('engine', config);
      setMsg('Saved');
      setTimeout(() => setMsg(''), 2000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="dim">Loading...</div>;
  if (!config) return <div className="error-text">{error}</div>;

  const updateWeight = (key: string, value: number) => {
    setConfig({ ...config, scoring_weights: { ...config.scoring_weights, [key]: value } });
  };

  const updateThreshold = (key: string, value: number) => {
    setConfig({ ...config, routing_thresholds: { ...config.routing_thresholds, [key]: value } });
  };

  const updateTrust = (key: string, value: number) => {
    setConfig({ ...config, source_initial_trust: { ...config.source_initial_trust, [key]: value } });
  };

  const updateList = (key: keyof EngineConfig, items: string[]) => {
    setConfig({ ...config, [key]: items });
  };

  return (
    <div>
      <div className="flex-between mb-2">
        <div>
          <h2 style={{ fontSize: 16 }}>Config / Engine</h2>
          <p className="dim small">Retune for any domain. Adjust scoring weights, routing thresholds, and domain vocabulary.</p>
        </div>
        <div className="flex">
          <button onClick={save} disabled={saving} className="primary">{saving ? 'Saving...' : 'Save'}</button>
          {msg && <span className="success-text">{msg}</span>}
        </div>
      </div>
      {error && <p className="error-text mb-2">{error}</p>}

      <div className="grid-2" style={{ gap: 24, alignItems: 'start' }}>
        <div>
          <h3 style={{ fontSize: 14, marginBottom: 8 }}>Scoring Weights</h3>
          {Object.entries(config.scoring_weights).map(([k, v]) => (
            <div key={k} className="flex-between" style={{ marginBottom: 6 }}>
              <span className="small">{k}</span>
              <div className="flex">
                <input type="range" min="0" max="2" step="0.1" value={v} onChange={(e) => updateWeight(k, parseFloat(e.target.value))} style={{ width: 100 }} />
                <span className="mono small" style={{ width: 32 }}>{v.toFixed(1)}</span>
              </div>
            </div>
          ))}

          <h3 style={{ fontSize: 14, margin: '16px 0 8px' }}>Routing Thresholds</h3>
          {Object.entries(config.routing_thresholds).map(([k, v]) => (
            <div key={k} className="flex-between" style={{ marginBottom: 6 }}>
              <span className="small">{k}</span>
              <div className="flex">
                <input type="range" min="0" max="10" step="0.1" value={v} onChange={(e) => updateThreshold(k, parseFloat(e.target.value))} style={{ width: 100 }} />
                <span className="mono small" style={{ width: 32 }}>{v.toFixed(1)}</span>
              </div>
            </div>
          ))}

          <div className="mt-4">
            <label>Queue Threshold</label>
            <input type="number" value={config.queue_threshold} onChange={(e) => setConfig({ ...config, queue_threshold: parseFloat(e.target.value) || 0 })} step="0.1" style={{ width: 100 }} />
          </div>
        </div>

        <div>
          <h3 style={{ fontSize: 14, marginBottom: 8 }}>Source Initial Trust</h3>
          {Object.entries(config.source_initial_trust).map(([k, v]) => (
            <div key={k} className="flex-between" style={{ marginBottom: 6 }}>
              <span className="small">{k}</span>
              <div className="flex">
                <input type="range" min="0" max="1" step="0.05" value={v} onChange={(e) => updateTrust(k, parseFloat(e.target.value))} style={{ width: 100 }} />
                <span className="mono small" style={{ width: 32 }}>{v.toFixed(2)}</span>
              </div>
            </div>
          ))}

          <EditableList label="Domain Terms" items={config.domain_terms} onChange={(v) => updateList('domain_terms', v)} />
          <EditableList
            label="Thought Leaders (Tier 0)"
            items={config.thought_leaders.tier0.names}
            onChange={(v) => setConfig({ ...config, thought_leaders: { ...config.thought_leaders, tier0: { ...config.thought_leaders.tier0, names: v } } })}
          />
          <EditableList
            label="Thought Leaders (Tier 1)"
            items={config.thought_leaders.tier1.names}
            onChange={(v) => setConfig({ ...config, thought_leaders: { ...config.thought_leaders, tier1: { ...config.thought_leaders.tier1, names: v } } })}
          />
          <EditableList label="Competitors" items={config.competitors} onChange={(v) => updateList('competitors', v)} />

          <div className="mt-4">
            <label>Conference Calendar</label>
            <div className="flex-wrap">
              {config.conference_calendar.map((c, i) => (
                <span key={i} className="tag" title={c.topics.join(', ')}>
                  {c.name} ({c.start.join('/')}–{c.end.join('/')})
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function EditableList({ label, items, onChange }: { label: string; items: string[]; onChange: (v: string[]) => void }) {
  const [input, setInput] = useState('');
  const add = () => { if (input.trim()) { onChange([...items, input.trim()]); setInput(''); } };

  return (
    <div className="mt-4">
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
