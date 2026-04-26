import { SessionState } from './types';

const API = process.env.NEXT_PUBLIC_FRONTEND_API_BASE_URL || 'http://localhost:8000';

export async function createSession(consult_type: string): Promise<string> {
  const res = await fetch(`${API}/sessions`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ consult_type }) });
  const data = await res.json();
  return data.session_id;
}

export async function submitDemoTranscript(sessionId: string, text: string) {
  return fetch(`${API}/sessions/${sessionId}/demo-transcript`, {
    method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ text }),
  });
}

export async function fetchState(sessionId: string): Promise<SessionState> {
  const res = await fetch(`${API}/sessions/${sessionId}/state`);
  if (!res.ok) throw new Error('Failed state');
  return res.json();
}

export async function deleteSession(sessionId: string) {
  return fetch(`${API}/sessions/${sessionId}`, { method: 'DELETE' });
}

export async function uploadAudio(sessionId: string, blob: Blob, idempotencyKey: string) {
  const form = new FormData();
  form.append('file', blob, 'chunk.webm');
  form.append('idempotency_key', idempotencyKey);
  return fetch(`${API}/sessions/${sessionId}/audio`, { method: 'POST', body: form });
}
