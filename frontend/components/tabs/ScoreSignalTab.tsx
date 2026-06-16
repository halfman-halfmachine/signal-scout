'use client';

import { useState, useEffect, useRef } from 'react';
import { api } from '@/lib/api';
import type { ScorePreview } from '@/lib/types';

const SLIDER_LAYERS = ['l1', 'l3', 'l4', 'l5', 'l7', 'l8', 'l10'];
const MULTIPLIER_LAYERS = ['l6', 'l9', 'l12'];
const TOGGLE_LAYERS = ['l2', 'l11'];

const LAYER_NAMES: Record<string, string> = {
  l1: 'Source Trust', l2: 'Recency Bonus', l3: 'Keyword Match', l4: 'Domain Relevance',
  l5: 'Novelty', l6: 'Thought Leader Mult', l7: 'Engagement', l8: 'Technical Depth',
  l9: 'Competitor Mult', l10: 'Sentiment Alignment', l11: 'Conference Timing', l12: 'Virality Mult',
};

function defaultLayers(): Record<string, number | boolean> {
  const l: Record<string, number | boolean> = {};
  SLIDER_LAYERS.forEach((k) => { l[k] = 0.5; });
  MULTIPLIER_LAYERS.forEach((k) => { l[k] = 1.0; });
  TOGGLE_LAYERS.forEach((k) => { l[k] = false; });
  return l;
}

export default function ScoreSignalTab() {
  const [form, setForm] = useState({ title: '', url: '', author: '', platform: '', domain: '', org: '', text: '', talking_points: '' });
  const [layers, setLayers] = useState<Record<string, number | boolean>>(defaultLayers);
  const [preview, setPreview] = useState<ScorePreview | null>(null);
  const [adding, setAdding] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      api.scorePreview(layers).then(setPreview).catch(() => {});
    }, 300);
  }, [layers]);

  const updateLayer = (key: string, value: number | boolean) => {
    setLayers({ ...layers, [key]: value });
  };

  const addToQueue = async () => {
    setAdding(true);
    setError('');
    try {
      await api.createSignal({ ...form, layers, kept: false });
      setMsg('Added to queue');
      setTimeout(() => setMsg(''), 2000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setAdding(false);
    }
  };

  const tierColor = (tier: string) => {
    const map: Record<string, string> = { IMMEDIATE: '#f87171', ROUTE: '#f97316', DIGEST: '#fbbf24', LOG: '#8888aa' };
    return map[tier] || '#8888aa';
  };

  return (
    <div>
      <div className="flex-between mb-2">
        <h2 style={{ fontSize: 16 }}>Score Signal</h2>
        {preview && (
          <div className="flex" style={{ gap: 12 }}>
            <span className="mono" style={{ fontSize: 20, color: tierColor(preview.tier) }}>{preview.score.toFixed(1)}</span>
            <span className="badge" style={{ background: tierColor(preview.tier), color: '#000' }}>{preview.tier}</span>
          </div>
        )}
      </div>

      <div className="grid-2" style={{ gap: 20, alignItems: 'start' }}>
        <div>
          <h3 style={{ fontSize: 14, marginBottom: 8 }}>Signal Details</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div><label>Title</label><input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
            <div><label>URL</label><input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} /></div>
            <div className="grid-2">
              <div><label>Author</label><input value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })} /></div>
              <div><label>Platform</label><input value={form.platform} onChange={(e) => setForm({ ...form, platform: e.target.value })} /></div>
            </div>
            <div className="grid-2">
              <div><label>Domain</label><input value={form.domain} onChange={(e) => setForm({ ...form, domain: e.target.value })} /></div>
              <div><label>Org</label><input value={form.org} onChange={(e) => setForm({ ...form, org: e.target.value })} /></div>
            </div>
            <div><label>Text</label><textarea value={form.text} onChange={(e) => setForm({ ...form, text: e.target.value })} rows={3} /></div>
            <div><label>Talking Points</label><textarea value={form.talking_points} onChange={(e) => setForm({ ...form, talking_points: e.target.value })} rows={2} /></div>
          </div>
        </div>

        <div>
          <h3 style={{ fontSize: 14, marginBottom: 8 }}>Layer Controls</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {SLIDER_LAYERS.map((k) => (
              <div key={k} className="flex-between">
                <span className="small">{LAYER_NAMES[k]}</span>
                <div className="flex">
                  <input type="range" min="0" max="1" step="0.05" value={layers[k] as number} onChange={(e) => updateLayer(k, parseFloat(e.target.value))} style={{ width: 120 }} />
                  <span className="mono small" style={{ width: 32, textAlign: 'right' }}>{(layers[k] as number).toFixed(2)}</span>
                </div>
              </div>
            ))}
            {MULTIPLIER_LAYERS.map((k) => (
              <div key={k} className="flex-between">
                <span className="small">{LAYER_NAMES[k]}</span>
                <div className="flex">
                  <input type="range" min="1" max="1.5" step="0.05" value={layers[k] as number} onChange={(e) => updateLayer(k, parseFloat(e.target.value))} style={{ width: 120 }} />
                  <span className="mono small" style={{ width: 32, textAlign: 'right' }}>{(layers[k] as number).toFixed(2)}</span>
                </div>
              </div>
            ))}
            {TOGGLE_LAYERS.map((k) => (
              <div key={k} className="flex-between">
                <span className="small">{LAYER_NAMES[k]}</span>
                <input type="checkbox" checked={layers[k] as boolean} onChange={(e) => updateLayer(k, e.target.checked)} style={{ width: 'auto' }} />
              </div>
            ))}
          </div>
          {preview && <p className="dim small mt-2" style={{ wordBreak: 'break-all' }}>Formula: {preview.formula}</p>}
        </div>
      </div>

      <div className="flex mt-4">
        <button className="primary" onClick={addToQueue} disabled={adding || !form.title}>{adding ? 'Adding...' : 'Add to Queue'}</button>
        {msg && <span className="success-text">{msg}</span>}
        {error && <span className="error-text">{error}</span>}
      </div>
    </div>
  );
}
