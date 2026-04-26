'use client';
import { useEffect, useRef, useState } from 'react';

export default function Recorder({enabled, onChunk}:{enabled:boolean; onChunk:(b:Blob)=>void}) {
  const [recording, setRecording] = useState(false);
  const recRef = useRef<MediaRecorder|null>(null);

  useEffect(()=>()=>{if(recRef.current && recRef.current.state!=='inactive') recRef.current.stop();},[]);

  const start = async () => {
    if (!navigator?.mediaDevices?.getUserMedia) return;
    const stream = await navigator.mediaDevices.getUserMedia({audio:true});
    const rec = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    recRef.current = rec;
    rec.ondataavailable = (e) => { if (e.data.size > 0) onChunk(e.data); };
    rec.start(6000);
    setRecording(true);
  };
  const stop = () => { recRef.current?.stop(); setRecording(false); };

  if (!enabled) return <div>Recording unavailable until session exists.</div>;
  return <div className="row"><button onClick={start} disabled={recording}>Start recording</button><button onClick={stop} disabled={!recording}>Stop recording</button><span>{recording?'Recording...':'Not recording'}</span></div>;
}
