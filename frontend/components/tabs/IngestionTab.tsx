'use client';

import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import type { IngestionConfig, IngestMeta, Topic } from '@/lib/types';

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
