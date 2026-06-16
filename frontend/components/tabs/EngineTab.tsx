'use client';

import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import type { EngineConfig, PlatformBaseline, ConferenceEntry, ThoughtLeaderTier } from '@/lib/types';

// Named, user-facing labels for the scoring weights. The base weights are the
// five that should sum to 1.0; the rest are internal input-blend ratios.
const BASE_WEIGHT_LABELS: Record<string, string> = {
  emergence_position: 'Emergence Position',
  relevance_depth: 'Relevance Depth',
  source_authority: 'Source Authority',
  question_gap_bonus: 'Question Gap Bonus',
  velocity_trajectory: 'Velocity Trajectory',
};
const BLEND_WEIGHT_LABELS: Record<string, string> = {
  ei_l1: 'Emergence ← L1 (detection) share',
  ei_l4: 'Emergence ← L4 (divergence) share',
  ri_l10: 'Relevance ← L10 (keywords) share',
  ri_l5: 'Relevance ← L5 (competitive gap) share',
};

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
  const updateList = (key: keyof EngineConfig, items: string[]) => {
    setConfig({ ...config, [key]: items });
  };
  const updateTier = (tier: 'tier0' | 'tier1', patch: Partial<ThoughtLeaderTier>) => {
    setConfig({
      ...config,
      thought_leaders: {
        ...config.thought_leaders,
        [tier]: { ...config.thought_leaders[tier], ...patch },
      },
    });
  };

  const weightKeys = Object.keys(config.scoring_weights);
  const baseKeys = weightKeys.filter((k) => k in BASE_WEIGHT_LABELS);
  const blendKeys = weightKeys.filter((k) => k in BLEND_WEIGHT_LABELS);
  const otherKeys = weightKeys.filter((k) => !(k in BASE_WEIGHT_LABELS) && !(k in BLEND_WEIGHT_LABELS));
  const baseSum = baseKeys.reduce((acc, k) => acc + (config.scoring_weights[k] || 0), 0);

  const weightRow = (k: string, label: string) => (
    <div key={k} className="flex-between" style={{ marginBottom: 6 }}>
      <span className="small">{label}</span>
      <div className="flex">
        <input type="range" min="0" max="2" step="0.05" value={config.scoring_weights[k]} onChange={(e) => updateWeight(k, parseFloat(e.target.value))} style={{ width: 100 }} />
        <span className="mono small" style={{ width: 36 }}>{config.scoring_weights[k].toFixed(2)}</span>
      </div>
    </div>
  );

  return (
    <div>
      <div className="flex-between mb-2">
        <div>
          <h2 style={{ fontSize: 16 }}>Config / Engine</h2>
          <p className="dim small">Retune for any domain. Every value the scoring engine reads is editable here.</p>
        </div>
        <div className="flex">
          <button onClick={save} disabled={saving} className="primary">{saving ? 'Saving...' : 'Save'}</button>
          {msg && <span className="success-text">{msg}</span>}
        </div>
      </div>
      {error && <p className="error-text mb-2">{error}</p>}

      {/* ── Scoring Math ─────────────────────────────────────────────── */}
      <div className="card mt-4">
        <h3 style={{ fontSize: 14, marginBottom: 12 }}>Scoring Math</h3>
        <div className="grid-2" style={{ gap: 24, alignItems: 'start' }}>
          <div>
            <p className="small dim mb-2">
              Base Weights — should sum to 1.0 (current: <span className="mono" style={{ color: Math.abs(baseSum - 1) < 0.001 ? 'var(--success)' : 'var(--text)' }}>{baseSum.toFixed(2)}</span>)
            </p>
            {baseKeys.map((k) => weightRow(k, BASE_WEIGHT_LABELS[k]))}
            {otherKeys.length > 0 && otherKeys.map((k) => weightRow(k, k))}
            <p className="small dim mt-4 mb-2">Input Blend Ratios</p>
            {blendKeys.map((k) => weightRow(k, BLEND_WEIGHT_LABELS[k]))}
          </div>
          <div>
            <h4 style={{ fontSize: 13, marginBottom: 8 }}>Routing Thresholds</h4>
            {Object.entries(config.routing_thresholds).map(([k, v]) => (
              <div key={k} className="flex-between" style={{ marginBottom: 6 }}>
                <span className="small">{k}</span>
                <div className="flex">
                  <input type="range" min="0" max="1" step="0.01" value={v} onChange={(e) => updateThreshold(k, parseFloat(e.target.value))} style={{ width: 100 }} />
                  <span className="mono small" style={{ width: 36 }}>{v.toFixed(2)}</span>
                </div>
              </div>
            ))}
            <div className="mt-4">
              <label>Queue Threshold</label>
              <input type="number" value={config.queue_threshold} onChange={(e) => setConfig({ ...config, queue_threshold: parseFloat(e.target.value) || 0 })} step="0.05" min="0" max="1" style={{ width: 100 }} />
            </div>
          </div>
        </div>
      </div>

      {/* ── Source Classification ────────────────────────────────────── */}
      <div className="card mt-4">
        <h3 style={{ fontSize: 14, marginBottom: 12 }}>Source Classification</h3>
        <div className="grid-2" style={{ gap: 24, alignItems: 'start' }}>
          <TrustEditor trust={config.source_initial_trust} onChange={(v) => setConfig({ ...config, source_initial_trust: v })} />
          <div>
            <EditableList label="Analyst Orgs" items={config.analyst_orgs} onChange={(v) => updateList('analyst_orgs', v)} />
            <EditableList label="Practitioner Domains" items={config.practitioner_domains} onChange={(v) => updateList('practitioner_domains', v)} />
            <EditableList label="Mainstream Domains" items={config.mainstream_domains} onChange={(v) => updateList('mainstream_domains', v)} />
          </div>
        </div>
      </div>

      {/* ── Vocabularies ─────────────────────────────────────────────── */}
      <div className="card mt-4">
        <h3 style={{ fontSize: 14, marginBottom: 12 }}>Vocabularies</h3>
        <div className="grid-2" style={{ gap: 24, alignItems: 'start' }}>
          <div>
            <EditableList label="Domain Terms" items={config.domain_terms} onChange={(v) => updateList('domain_terms', v)} />
            <EditableList label="Tech Terms" items={config.tech_terms} onChange={(v) => updateList('tech_terms', v)} />
            <EditableList label="Noise Patterns (regex, case-insensitive)" items={config.noise_patterns} onChange={(v) => updateList('noise_patterns', v)} />
          </div>
          <div>
            <p className="small dim mb-2">Hype Cycle Vocab</p>
            <EditableList label="Hype" items={config.hype_vocab} onChange={(v) => updateList('hype_vocab', v)} />
            <EditableList label="Trough" items={config.trough_vocab} onChange={(v) => updateList('trough_vocab', v)} />
            <EditableList label="Practical" items={config.practical_vocab} onChange={(v) => updateList('practical_vocab', v)} />
            <EditableList label="Plateau" items={config.plateau_vocab} onChange={(v) => updateList('plateau_vocab', v)} />
          </div>
        </div>
      </div>

      {/* ── Engagement & Platforms ───────────────────────────────────── */}
      <div className="card mt-4">
        <h3 style={{ fontSize: 14, marginBottom: 12 }}>Engagement & Platforms</h3>
        <div className="grid-2" style={{ gap: 24, alignItems: 'start' }}>
          <PlatformBaselineEditor baselines={config.platform_baselines} onChange={(v) => setConfig({ ...config, platform_baselines: v })} />
          <NumberArrayEditor label="Heat Multipliers (index = platform count)" items={config.heat_multipliers} onChange={(v) => setConfig({ ...config, heat_multipliers: v })} />
        </div>
      </div>

      {/* ── Thought Leaders, Competitors & Calendar ──────────────────── */}
      <div className="card mt-4">
        <h3 style={{ fontSize: 14, marginBottom: 12 }}>Thought Leaders, Competitors & Calendar</h3>
        <div className="grid-2" style={{ gap: 24, alignItems: 'start' }}>
          <div>
            <div className="flex-between" style={{ marginBottom: 6 }}>
              <label style={{ margin: 0 }}>Tier 0 — weight</label>
              <input type="number" value={config.thought_leaders.tier0.weight} step="0.01" min="0" max="1" style={{ width: 80 }} onChange={(e) => updateTier('tier0', { weight: parseFloat(e.target.value) || 0 })} />
            </div>
            <EditableList label="Tier 0 Names" items={config.thought_leaders.tier0.names} onChange={(v) => updateTier('tier0', { names: v })} />
            <EditableList label="Tier 0 Handles" items={config.thought_leaders.tier0.handles ?? []} onChange={(v) => updateTier('tier0', { handles: v })} />

            <div className="flex-between mt-4" style={{ marginBottom: 6 }}>
              <label style={{ margin: 0 }}>Tier 1 — weight</label>
              <input type="number" value={config.thought_leaders.tier1.weight} step="0.01" min="0" max="1" style={{ width: 80 }} onChange={(e) => updateTier('tier1', { weight: parseFloat(e.target.value) || 0 })} />
            </div>
            <EditableList label="Tier 1 Names" items={config.thought_leaders.tier1.names} onChange={(v) => updateTier('tier1', { names: v })} />
            <EditableList label="Tier 1 Domains" items={config.thought_leaders.tier1.domains ?? []} onChange={(v) => updateTier('tier1', { domains: v })} />

            <EditableList label="Competitors" items={config.competitors} onChange={(v) => updateList('competitors', v)} />
          </div>
          <ConferenceEditor entries={config.conference_calendar} onChange={(v) => setConfig({ ...config, conference_calendar: v })} />
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

// Source trust: edit values per domain AND add/remove domain keys.
function TrustEditor({ trust, onChange }: { trust: Record<string, number>; onChange: (v: Record<string, number>) => void }) {
  const [domain, setDomain] = useState('');
  const [value, setValue] = useState(0.7);

  const add = () => {
    const key = domain.trim().toLowerCase().replace(/^www\./, '');
    if (!key) return;
    onChange({ ...trust, [key]: value });
    setDomain('');
  };
  const remove = (key: string) => {
    const next = { ...trust };
    delete next[key];
    onChange(next);
  };
  const update = (key: string, v: number) => onChange({ ...trust, [key]: v });

  return (
    <div>
      <label>Source Initial Trust</label>
      <div className="flex mb-2" style={{ gap: 4 }}>
        <input value={domain} onChange={(e) => setDomain(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), add())} placeholder="domain.com" style={{ flex: 1 }} />
        <input type="number" value={value} step="0.05" min="0" max="1" onChange={(e) => setValue(parseFloat(e.target.value) || 0)} style={{ width: 64 }} />
        <button onClick={add} type="button">+</button>
      </div>
      {Object.entries(trust).map(([k, v]) => (
        <div key={k} className="flex-between" style={{ marginBottom: 6 }}>
          <span className="small">{k}</span>
          <div className="flex">
            <input type="range" min="0" max="1" step="0.05" value={v} onChange={(e) => update(k, parseFloat(e.target.value))} style={{ width: 90 }} />
            <span className="mono small" style={{ width: 32 }}>{v.toFixed(2)}</span>
            <span className="remove" onClick={() => remove(k)}>×</span>
          </div>
        </div>
      ))}
    </div>
  );
}

// Per-platform 24h engagement baselines. "blog" is the engine's fallback and
// cannot be removed.
function PlatformBaselineEditor({ baselines, onChange }: { baselines: Record<string, PlatformBaseline>; onChange: (v: Record<string, PlatformBaseline>) => void }) {
  const [platform, setPlatform] = useState('');

  const add = () => {
    const key = platform.trim().toLowerCase();
    if (!key || baselines[key]) return;
    onChange({ ...baselines, [key]: { reactions: 0, comments: 0, shares: 0 } });
    setPlatform('');
  };
  const remove = (key: string) => {
    if (key === 'blog') return; // engine fallback baseline — keep it
    const next = { ...baselines };
    delete next[key];
    onChange(next);
  };
  const update = (key: string, field: keyof PlatformBaseline, v: number) =>
    onChange({ ...baselines, [key]: { ...baselines[key], [field]: v } });

  return (
    <div>
      <label>Platform Baselines (24h reactions / comments / shares)</label>
      <div className="flex mb-2" style={{ gap: 4 }}>
        <input value={platform} onChange={(e) => setPlatform(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), add())} placeholder="platform" style={{ flex: 1 }} />
        <button onClick={add} type="button">+</button>
      </div>
      {Object.entries(baselines).map(([key, val]) => (
        <div key={key} className="flex" style={{ gap: 4, marginBottom: 6, alignItems: 'center' }}>
          <span className="tag" style={{ minWidth: 72 }}>{key}</span>
          {(['reactions', 'comments', 'shares'] as const).map((field) => (
            <input key={field} type="number" value={val[field]} title={field} min="0" onChange={(e) => update(key, field, parseInt(e.target.value) || 0)} style={{ width: 60 }} />
          ))}
          {key !== 'blog' && <span className="remove" onClick={() => remove(key)}>×</span>}
        </div>
      ))}
    </div>
  );
}

// Fixed-meaning numeric array (index carries meaning). Keep at least one entry.
function NumberArrayEditor({ label, items, onChange }: { label: string; items: number[]; onChange: (v: number[]) => void }) {
  const update = (i: number, v: number) => {
    const next = [...items];
    next[i] = v;
    onChange(next);
  };
  const add = () => onChange([...items, 1.0]);
  const remove = (i: number) => { if (items.length > 1) onChange(items.filter((_, j) => j !== i)); };

  return (
    <div>
      <label>{label}</label>
      <div className="flex-wrap mb-2" style={{ gap: 6 }}>
        {items.map((v, i) => (
          <div key={i} className="flex" style={{ gap: 2, alignItems: 'center' }}>
            <span className="small dim mono">[{i}]</span>
            <input type="number" value={v} step="0.1" min="0" onChange={(e) => update(i, parseFloat(e.target.value) || 0)} style={{ width: 60 }} />
            {items.length > 1 && <span className="remove" onClick={() => remove(i)}>×</span>}
          </div>
        ))}
      </div>
      <button type="button" onClick={add} style={{ fontSize: 12 }}>+ Add</button>
    </div>
  );
}

// Conference calendar entries: {name, start:[m,d], end:[m,d], topics:[]}.
function ConferenceEditor({ entries, onChange }: { entries: ConferenceEntry[]; onChange: (v: ConferenceEntry[]) => void }) {
  const [name, setName] = useState('');
  const [startM, setStartM] = useState(1);
  const [startD, setStartD] = useState(1);
  const [endM, setEndM] = useState(1);
  const [endD, setEndD] = useState(1);
  const [topics, setTopics] = useState('');

  const add = () => {
    if (!name.trim()) return;
    const ts = topics.split(',').map((t) => t.trim()).filter(Boolean);
    onChange([...entries, { name: name.trim(), start: [startM, startD], end: [endM, endD], topics: ts }]);
    setName(''); setStartM(1); setStartD(1); setEndM(1); setEndD(1); setTopics('');
  };
  const remove = (i: number) => onChange(entries.filter((_, j) => j !== i));

  return (
    <div>
      <label>Conference Calendar</label>
      <div className="flex mb-2" style={{ gap: 4, flexWrap: 'wrap' }}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Conference name" style={{ width: '100%' }} />
        <span className="small dim">start</span>
        <input type="number" value={startM} min="1" max="12" title="Start month" onChange={(e) => setStartM(parseInt(e.target.value) || 1)} style={{ width: 48 }} />
        <input type="number" value={startD} min="1" max="31" title="Start day" onChange={(e) => setStartD(parseInt(e.target.value) || 1)} style={{ width: 48 }} />
        <span className="small dim">end</span>
        <input type="number" value={endM} min="1" max="12" title="End month" onChange={(e) => setEndM(parseInt(e.target.value) || 1)} style={{ width: 48 }} />
        <input type="number" value={endD} min="1" max="31" title="End day" onChange={(e) => setEndD(parseInt(e.target.value) || 1)} style={{ width: 48 }} />
        <input value={topics} onChange={(e) => setTopics(e.target.value)} placeholder="topics (comma-separated)" style={{ flex: 1 }} />
        <button onClick={add} type="button">+</button>
      </div>
      <div className="flex-wrap">
        {entries.map((c, i) => (
          <span key={i} className="tag" title={c.topics.join(', ')}>
            {c.name} ({c.start.join('/')}–{c.end.join('/')})
            <span className="remove" onClick={() => remove(i)}>×</span>
          </span>
        ))}
      </div>
    </div>
  );
}
