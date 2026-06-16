'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import type { QueueView, GenerateOutput, AppSettings } from '@/lib/types';

export default function OutputStudioTab({ signal }: { signal: QueueView | null }) {
  const [outputs, setOutputs] = useState<GenerateOutput[]>([]);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const loadSettings = useCallback(async () => {
    try {
      const s = await api.getConfig<AppSettings>('app_settings');
      setSettings(s);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { loadSettings(); }, [loadSettings]);

  const generate = async () => {
    if (!signal || !settings) return;
    setGenerating(true);
    setError('');
    try {
      const activeLenses = settings.lenses.filter((l) => l.active).map((l) => l.id);
      const res = await api.generate({
        output_types: settings.output_types,
        signal: { url: signal.url, title: signal.title, author: signal.author, platform: signal.platform, domain: signal.domain, org: '', text: signal.text, talking_points: signal.talking_points },
        framework_id: settings.frameworks[0]?.id || '',
        social_platform: settings.social_platforms[0] || '',
        score: signal.score,
        tier: signal.tier,
        layers: signal.layers,
        active_lens_ids: activeLenses,
        input_mode_id: settings.input_modes[0] || '',
        persona_ids: settings.personas.slice(0, 1),
        pov_ids: settings.pov_options.slice(0, 1),
        pov_custom: '',
        web_research: true,
        variant: outputs.length,
        signal_id: signal.id,
      });
      setOutputs((prev) => [...prev, ...res.outputs]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const regenerateVariant = async (output: GenerateOutput) => {
    if (!signal || !settings) return;
    setGenerating(true);
    try {
      const activeLenses = settings.lenses.filter((l) => l.active).map((l) => l.id);
      const res = await api.generate({
        output_types: [output.output_type],
        signal: { url: signal.url, title: signal.title, author: signal.author, platform: signal.platform, domain: signal.domain, org: '', text: signal.text, talking_points: signal.talking_points },
        framework_id: settings.frameworks[0]?.id || '',
        social_platform: settings.social_platforms[0] || '',
        score: signal.score,
        tier: signal.tier,
        layers: signal.layers,
        active_lens_ids: activeLenses,
        input_mode_id: settings.input_modes[0] || '',
        persona_ids: settings.personas.slice(0, 1),
        pov_ids: settings.pov_options.slice(0, 1),
        pov_custom: '',
        web_research: true,
        variant: output.variant + 1,
        signal_id: signal.id,
      });
      setOutputs((prev) => [...prev, ...res.outputs]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setGenerating(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).catch(() => {});
  };

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const combineSelected = () => {
    const combined = outputs.filter((o) => selected.has(o.id)).map((o) => o.content).join('\n\n---\n\n');
    const newOutput: GenerateOutput = {
      id: `combined_${Date.now()}`,
      output_type: 'combined',
      output_type_name: 'Combined',
      framework: 'mixed',
      content: combined,
      is_live: false,
      variant: 0,
    };
    setOutputs((prev) => [...prev, newOutput]);
    setSelected(new Set());
  };

  if (!signal) {
    return (
      <div>
        <h2 style={{ fontSize: 16, marginBottom: 8 }}>Output Studio</h2>
        <p className="dim">Select a signal from the Signal Queue tab (click &quot;Generate Outputs&quot;) to begin.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex-between mb-2">
        <div>
          <h2 style={{ fontSize: 16 }}>Output Studio</h2>
          <p className="small dim">Signal: {signal.title}</p>
        </div>
        <div className="flex">
          {selected.size >= 2 && <button onClick={combineSelected}>Combine ({selected.size})</button>}
          <button className="primary" onClick={generate} disabled={generating}>
            {generating ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </div>
      {error && <p className="error-text mb-2">{error}</p>}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {outputs.map((o) => (
          <div key={o.id} className="card" style={{ borderColor: selected.has(o.id) ? 'var(--accent)' : undefined }}>
            <div className="flex-between mb-2">
              <div className="flex">
                <input type="checkbox" checked={selected.has(o.id)} onChange={() => toggleSelect(o.id)} style={{ width: 'auto' }} />
                <strong>{o.output_type_name}</strong>
                <span className="dim small">({o.framework})</span>
                <span className="badge" style={{ background: o.is_live ? 'var(--success)' : 'var(--border)', color: o.is_live ? '#000' : 'var(--text-dim)' }}>
                  {o.is_live ? 'LIVE' : 'TEMPLATE'}
                </span>
              </div>
              <div className="flex">
                <button onClick={() => copyToClipboard(o.content)} style={{ fontSize: 11 }}>Copy</button>
                <button onClick={() => regenerateVariant(o)} style={{ fontSize: 11 }}>Variant</button>
              </div>
            </div>
            <div contentEditable suppressContentEditableWarning style={{ background: 'var(--bg-input)', padding: 10, borderRadius: 4, fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap', minHeight: 60, outline: 'none' }}>
              {o.content}
            </div>
          </div>
        ))}
        {outputs.length === 0 && <p className="dim">Click Generate to create outputs for this signal.</p>}
      </div>
    </div>
  );
}
