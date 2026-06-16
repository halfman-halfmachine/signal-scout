'use client';

import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import type { IngestionConfig, IngestionPreset, IngestMeta, Topic } from '@/lib/types';

export default function IngestionTab() {
  const [config, setConfig] = useState<IngestionConfig | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selectedTopic, setSelectedTopic] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [ingestResult, setIngestResult] = useState<IngestMeta | null>(null);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');

  const load = useCallback(async () => {
    try {
      const [cfg, t] = await Promise.all([
        api.getConfig<IngestionConfig>('ingestion'),
        api.getTopics(),
      ]);
      setConfig(cfg);
      setTopics(t.topics);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    if (!config) return;
    setSaving(true);
    setMsg('');
    try {
      await api.putConfig('ingestion', config);
      setMsg('Saved');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const runIngest = async () => {
    setIngesting(true);
    setIngestResult(null);
    try {
      const res = await api.ingest(selectedTopic || undefined);
      setIngestResult(res.meta);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Ingest failed');
    } finally {
      setIngesting(false);
    }
  };

  if (loading) return <div className="dim">Loading...</div>;
  if (!config) return <div className="error-text">{error}</div>;

  const updateList = (key: keyof IngestionConfig, value: string[]) => {
    setConfig({ ...config, [key]: value });
  };

  return (
    <div>
      <div className="flex-between mb-2">
        <h2 style={{ fontSize: 16 }}>Ingestion Config</h2>
        <div className="flex">
          <button onClick={save} disabled={saving}>{saving ? 'Saving...' : 'Save Config'}</button>
          {msg && <span className="success-text">{msg}</span>}
        </div>
      </div>
      {error && <p className="error-text mb-2">{error}</p>}

      <div className="grid-2 mt-4" style={{ gap: 20 }}>
        <ListEditor label="HN Queries" items={config.hn_queries} onChange={(v) => updateList('hn_queries', v)} />
        <div>
          <label>Reddit Subs (comma-separated)</label>
          <input value={config.reddit_subs} onChange={(e) => setConfig({ ...config, reddit_subs: e.target.value })} />
        </div>
        <ListEditor label="Arxiv Feeds" items={config.arxiv_feeds} onChange={(v) => updateList('arxiv_feeds', v)} />
        <FeedEditor label="Competitor Feeds" feeds={config.competitor_feeds} onChange={(feeds) => setConfig({ ...config, competitor_feeds: feeds })} />
        <FeedEditor label="News Feeds" feeds={config.news_feeds} onChange={(feeds) => setConfig({ ...config, news_feeds: feeds })} />
        <FeedEditor label="Analyst Feeds" feeds={config.analyst_feeds} onChange={(feeds) => setConfig({ ...config, analyst_feeds: feeds })} />
      </div>

      <PresetsEditor presets={config.presets} onChange={(p) => setConfig({ ...config, presets: p })} />

      <div className="card mt-4">
        <h3 style={{ fontSize: 14, marginBottom: 8 }}>Run Ingest Now</h3>
        <div className="flex">
          <select value={selectedTopic} onChange={(e) => setSelectedTopic(e.target.value)} style={{ width: 200 }}>
            <option value="">All sources</option>
            {topics.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
          </select>
          <button className="primary" onClick={runIngest} disabled={ingesting}>
            {ingesting ? 'Ingesting...' : 'Run Ingest'}
          </button>
        </div>
        {ingestResult && (
          <div className="mt-2 small">
            <p>Ingested <strong className="mono">{ingestResult.count}</strong> signals ({ingestResult.mode}, topic: {ingestResult.topic || 'all'})</p>
            <p className="dim">Sources: {Object.entries(ingestResult.sources).map(([k, v]) => `${k}: ${v}`).join(', ')}</p>
            {ingestResult.errors.length > 0 && <p className="error-text">Errors: {ingestResult.errors.join('; ')}</p>}
          </div>
        )}
      </div>
    </div>
  );
}

function ListEditor({ label, items, onChange }: { label: string; items: string[]; onChange: (v: string[]) => void }) {
  const [input, setInput] = useState('');
  const add = () => {
    if (input.trim()) { onChange([...items, input.trim()]); setInput(''); }
  };
  return (
    <div>
      <label>{label}</label>
      <div className="flex mb-2">
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

function PresetsEditor({ presets, onChange }: { presets: Record<string, IngestionPreset>; onChange: (v: Record<string, IngestionPreset>) => void }) {
  const [key, setKey] = useState('');

  const add = () => {
    const k = key.trim().toLowerCase().replace(/\s+/g, '-');
    if (!k || presets[k]) return;
    onChange({ ...presets, [k]: { label: key.trim(), hn: [], reddit: '' } });
    setKey('');
  };
  const remove = (k: string) => {
    const next = { ...presets };
    delete next[k];
    onChange(next);
  };
  const update = (k: string, patch: Partial<IngestionPreset>) =>
    onChange({ ...presets, [k]: { ...presets[k], ...patch } });

  return (
    <div className="card mt-4">
      <div className="flex-between mb-2">
        <div>
          <h3 style={{ fontSize: 14 }}>Topic Presets</h3>
          <p className="dim small">Focused ingestion bundles. Selecting a topic on Run Ingest swaps in that preset&apos;s queries.</p>
        </div>
        <div className="flex">
          <input value={key} onChange={(e) => setKey(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), add())} placeholder="New topic key" style={{ width: 160 }} />
          <button onClick={add} type="button">+ Add Preset</button>
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {Object.entries(presets).map(([k, p]) => (
          <div key={k} className="card">
            <div className="flex-between">
              <div className="grid-2" style={{ flex: 1, gap: 8 }}>
                <div><label>Topic Key (id)</label><input value={k} disabled style={{ opacity: 0.6 }} /></div>
                <div><label>Label</label><input value={p.label} onChange={(e) => update(k, { label: e.target.value })} /></div>
              </div>
              <button onClick={() => remove(k)} style={{ color: 'var(--error)', border: 'none', marginLeft: 8 }}>Remove</button>
            </div>
            <div className="mt-2">
              <label>Reddit Subs (comma-separated)</label>
              <input value={p.reddit} onChange={(e) => update(k, { reddit: e.target.value })} />
            </div>
            <ListEditor label="HN Queries" items={p.hn} onChange={(v) => update(k, { hn: v })} />
          </div>
        ))}
        {Object.keys(presets).length === 0 && <p className="dim small">No presets. Add a topic key to create a focused ingestion bundle.</p>}
      </div>
    </div>
  );
}

function FeedEditor({ label, feeds, onChange }: { label: string; feeds: { name: string; domain: string; url: string }[]; onChange: (v: { name: string; domain: string; url: string }[]) => void }) {
  const [name, setName] = useState('');
  const [domain, setDomain] = useState('');
  const [url, setUrl] = useState('');

  const add = () => {
    if (name && url) { onChange([...feeds, { name, domain, url }]); setName(''); setDomain(''); setUrl(''); }
  };

  return (
    <div>
      <label>{label}</label>
      <div className="flex mb-2" style={{ gap: 4 }}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" style={{ width: '30%' }} />
        <input value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="Domain" style={{ width: '25%' }} />
        <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="URL" style={{ width: '35%' }} />
        <button onClick={add} type="button">+</button>
      </div>
      {feeds.map((f, i) => (
        <div key={i} className="flex mb-2">
          <span className="tag">{f.name} ({f.domain})<span className="remove" onClick={() => onChange(feeds.filter((_, j) => j !== i))}>×</span></span>
        </div>
      ))}
    </div>
  );
}
