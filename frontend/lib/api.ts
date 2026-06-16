import type {
  AuthStatus,
  HealthStatus,
  QueueView,
  IngestMeta,
  ScorePreview,
  GenerateOutput,
  Topic,
} from './types';

const BASE = process.env.NEXT_PUBLIC_API_BASE || '';

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...opts.headers as Record<string, string> },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(body.error || body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => request<HealthStatus>('/api/health'),

  authStatus: () => request<AuthStatus>('/api/auth/status'),
  login: (password: string) => request<{ ok: boolean; error?: string }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ password }) }),
  logout: () => request<{ ok: boolean }>('/api/auth/logout', { method: 'POST' }),

  getConfig: <T>(section: string) => request<T>(`/api/config/${section}`),
  putConfig: (section: string, data: unknown) => request<{ ok: boolean }>(`/api/config/${section}`, { method: 'PUT', body: JSON.stringify({ data }) }),

  getTopics: () => request<{ topics: Topic[] }>('/api/topics'),
  ingest: (topic?: string) => request<{ signals: QueueView[]; meta: IngestMeta }>(`/api/ingest${topic ? `?topic=${encodeURIComponent(topic)}` : ''}`, { method: 'POST' }),

  getSignals: (opts?: { include_dismissed?: boolean; min_score?: number; limit?: number }) => {
    const params = new URLSearchParams();
    if (opts?.include_dismissed) params.set('include_dismissed', 'true');
    if (opts?.min_score !== undefined) params.set('min_score', String(opts.min_score));
    if (opts?.limit !== undefined) params.set('limit', String(opts.limit));
    const qs = params.toString();
    return request<{ signals: QueueView[]; count: number }>(`/api/signals${qs ? `?${qs}` : ''}`);
  },
  createSignal: (body: Record<string, unknown>) => request<{ ok: boolean; signal: QueueView }>('/api/signals', { method: 'POST', body: JSON.stringify(body) }),
  patchSignal: (id: string, body: Record<string, unknown>) => request<{ ok: boolean; signal: QueueView }>(`/api/signals/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteSignal: (id: string) => request<{ ok: boolean }>(`/api/signals/${id}`, { method: 'DELETE' }),

  scorePreview: (layers: Record<string, number | boolean>) => request<ScorePreview>('/api/score-preview', { method: 'POST', body: JSON.stringify({ layers }) }),
  feedback: (body: { signal_id?: string; domain?: string; was_valuable: boolean }) => request<{ ok: boolean; domain: string; source_trust: number }>('/api/feedback', { method: 'POST', body: JSON.stringify(body) }),

  generate: (body: Record<string, unknown>) => request<{ outputs: GenerateOutput[] }>('/api/generate', { method: 'POST', body: JSON.stringify(body) }),
  getOutputs: (limit?: number) => request<{ outputs: GenerateOutput[] }>(`/api/outputs${limit ? `?limit=${limit}` : ''}`),
};
