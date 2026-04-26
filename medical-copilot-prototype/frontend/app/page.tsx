'use client';
import { useEffect, useMemo, useState } from 'react';
import ConsultSelector from './components/ConsultSelector';
import SafetyBanner from './components/SafetyBanner';
import SuggestionPanel from './components/SuggestionPanel';
import DifferentialPanel from './components/DifferentialPanel';
import TranscriptPanel from './components/TranscriptPanel';
import DeleteSessionButton from './components/DeleteSessionButton';
import Recorder from './components/Recorder';
import { createSession, deleteSession, fetchState, submitDemoTranscript, uploadAudio } from '@/lib/api';
import { SessionState } from '@/lib/types';

const FIXTURES: Record<string, string> = {
  chest_discomfort: `Doctor: What brings you in today?\nPatient: I have chest discomfort after meals.\nDoctor: How long has this been happening?\nPatient: About two weeks.\nDoctor: Does it happen with exercise?\nPatient: I am not sure, I mostly notice it after eating.\nDoctor: Any shortness of breath or fainting?\nPatient: No fainting, but I have not thought much about shortness of breath.`,
  palpitations: `Doctor: What are you noticing?\nPatient: My heart sometimes races at night.\nDoctor: Do you drink coffee or energy drinks?\nPatient: I drink three coffees and sometimes energy drinks.\nDoctor: Have you fainted?\nPatient: No.`,
  abdominal_pain: `Doctor: What is the main issue?\nPatient: I have abdominal pain after eating.\nDoctor: Any vomiting blood or black stools?\nPatient: No.\nDoctor: Any weight loss?\nPatient: I lost a little weight but I am not sure how much.`,
  headache: `Doctor: Tell me about the headache.\nPatient: It started yesterday and is very painful.\nDoctor: Any weakness, trouble speaking, or vision loss?\nPatient: No weakness or speech trouble.\nDoctor: Did it start suddenly like a thunderclap?\nPatient: I do not know, it got bad quickly.`
}

export default function Page() {
  const [consultType, setConsultType] = useState('internal_medicine');
  const [sessionId, setSessionId] = useState<string>('');
  const [state, setState] = useState<SessionState | null>(null);
  const [fixture, setFixture] = useState('chest_discomfort');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!sessionId) return;
    let mounted = true;
    const id = setInterval(async () => {
      try {
        const s = await fetchState(sessionId);
        if (mounted) setState(s);
      } catch {
        if (mounted) setError('Network issue while polling; showing last stable state.');
      }
    }, 3000);
    return () => { mounted = false; clearInterval(id); };
  }, [sessionId]);

  const create = async () => {
    const sid = await createSession(consultType);
    setSessionId(sid);
    setError('');
  };

  const runDemo = async () => {
    if (!sessionId) return;
    await submitDemoTranscript(sessionId, FIXTURES[fixture]);
    const s = await fetchState(sessionId);
    setState(s);
  };

  const onChunk = async (b: Blob) => {
    if (!sessionId) return;
    const key = `${Date.now()}_${Math.random()}`;
    await uploadAudio(sessionId, b, key);
  };

  const remove = async () => {
    if (!sessionId) return;
    await deleteSession(sessionId);
    setSessionId('');
    setState(null);
  };

  const analysis = useMemo(()=>state?.analysis_status ?? 'pending', [state]);

  return (
    <main>
      <h1>Clinical Interview Copilot</h1>
      <SafetyBanner />
      <div className="panel row">
        <ConsultSelector value={consultType} onChange={setConsultType} />
        <button onClick={create}>Create session</button>
        <Recorder enabled={!!sessionId} onChunk={onChunk} />
        <select value={fixture} onChange={(e)=>setFixture(e.target.value)}>
          {Object.keys(FIXTURES).map(k => <option key={k} value={k}>{k}</option>)}
        </select>
        <button onClick={runDemo} disabled={!sessionId}>Load Fixture Demo Transcript</button>
        <DeleteSessionButton onDelete={remove} disabled={!sessionId} />
      </div>

      {!sessionId && <div className="panel">No session yet.</div>}
      {error && <div className="panel">{error}</div>}
      <div className="panel">Analysis status: {analysis}</div>
      <SuggestionPanel items={state?.suggestions || []} />
      <DifferentialPanel items={state?.differentials || []} />
      <TranscriptPanel transcript={state?.transcript || ''} />
    </main>
  );
}
