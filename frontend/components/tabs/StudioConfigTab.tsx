'use client';

import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import type { AppSettings } from '@/lib/types';

export default function StudioConfigTab() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(true);
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

  if (loading) return <div className="dim">Loading...</div>;
  if (!settings) return <div className="error-text">{error}</div>;

  return (
    <div>
      <div className="flex-between mb-2">
        <h2 style={{ fontSize: 16 }}>Studio Config</h2>
      </div>
      <p className="dim small mb-2">
        The Output Studio draws on the catalogs below. Generation uses the server&apos;s configured key or falls back to templates.
      </p>

      <div className="grid-2" style={{ gap: 20, alignItems: 'start' }}>
        <Catalog
          label="Output Types"
          items={settings.output_types.map((o) => ({ name: o.name, desc: o.desc }))}
        />
        <Catalog
          label="Social Platforms"
          items={settings.social_platforms.map((p) => ({ name: p.name }))}
        />
        <Catalog
          label="Input Modes"
          items={settings.input_modes.map((m) => ({ name: m.name, desc: m.desc }))}
        />
        <Catalog
          label="POV Options"
          items={settings.pov_options.map((p) => ({ name: p.name, desc: p.desc }))}
        />
        <Catalog
          label="Personas"
          items={settings.personas.map((p) => ({ name: p.name, desc: p.archetype }))}
        />
      </div>
    </div>
  );
}

function Catalog({ label, items }: { label: string; items: { name: string; desc?: string }[] }) {
  return (
    <div>
      <label>{label}</label>
      <div className="flex-wrap" style={{ gap: 6 }}>
        {items.map((item, i) => (
          <span key={i} className="tag" title={item.desc ?? ''}>{item.name}</span>
        ))}
      </div>
    </div>
  );
}
