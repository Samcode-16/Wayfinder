import { parseSSE, type ServerEvent } from './sse';

export interface Health {
  status: string;
  llm_providers: string[];
  live_travel_data: boolean;
  geoapify_api_key?: string | null;
}

export interface ChatBody {
  thread_id?: string;
  message?: string;
  resume?: unknown;
}

export async function getHealth(signal?: AbortSignal): Promise<Health> {
  const r = await fetch('/api/health', { signal });
  if (!r.ok) throw new Error(`Health check failed (${r.status})`);
  return r.json();
}

export async function* streamChat(body: ChatBody, signal: AbortSignal): AsyncGenerator<ServerEvent> {
  const r = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!r.ok || !r.body) throw new Error(`The server returned ${r.status}. Is the backend running on port 8000?`);
  yield* parseSSE(r.body);
}

export interface EmailPayload {
  email: string;
  thread_id?: string;
  plan?: unknown;
  request?: unknown;
  selection?: unknown;
  flights?: unknown[];
  hotels?: unknown[];
}

export async function sendItineraryEmail(
  payload: EmailPayload,
  signal?: AbortSignal
): Promise<{ ok: boolean; status: string; message: string }> {
  const r = await fetch('/api/email', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to send email (${r.status})`);
  }
  return r.json();
}
