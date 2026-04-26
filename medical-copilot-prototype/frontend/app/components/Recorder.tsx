'use client';

import { useEffect, useRef, useState } from 'react';

const RECORDING_CHUNK_MS = 25_000;
const RESTART_DELAY_MS = 500;
const MIN_CHUNK_SIZE_BYTES = 1000;

export default function Recorder({
  enabled,
  onChunk,
}: {
  enabled: boolean;
  onChunk: (b: Blob) => void;
}) {
  const [recording, setRecording] = useState(false);
  const [status, setStatus] = useState('Not recording');

  const streamRef = useRef<MediaStream | null>(null);
  const recRef = useRef<MediaRecorder | null>(null);
  const shouldContinueRef = useRef(false);
  const timeoutRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      shouldContinueRef.current = false;

      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current);
      }

      if (recRef.current && recRef.current.state !== 'inactive') {
        recRef.current.stop();
      }

      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  const getMimeType = () => {
    if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
      return 'audio/webm;codecs=opus';
    }

    if (MediaRecorder.isTypeSupported('audio/webm')) {
      return 'audio/webm';
    }

    return '';
  };

  const recordOneCompleteChunk = () => {
    if (!streamRef.current || !shouldContinueRef.current) return;

    const mimeType = getMimeType();

    const rec = mimeType
      ? new MediaRecorder(streamRef.current, { mimeType })
      : new MediaRecorder(streamRef.current);

    recRef.current = rec;

    const parts: BlobPart[] = [];

    rec.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        parts.push(e.data);
      }
    };

    rec.onstop = () => {
      const blob = new Blob(parts, {
        type: rec.mimeType || mimeType || 'audio/webm',
      });

      console.log('Complete audio chunk:', blob.size, blob.type);

      if (blob.size >= MIN_CHUNK_SIZE_BYTES) {
        onChunk(blob);
        setStatus('Uploaded 25-second chunk. Recording next chunk...');
      } else {
        console.log('Skipping tiny/empty chunk:', blob.size);
        setStatus('Skipped empty chunk. Recording next chunk...');
      }

      if (shouldContinueRef.current) {
        timeoutRef.current = window.setTimeout(
          recordOneCompleteChunk,
          RESTART_DELAY_MS
        );
      }
    };

    rec.onerror = (event) => {
      console.error('Recorder error:', event);
      setStatus('Recorder error. Try stopping and starting again.');
    };

    rec.start();
    setStatus('Recording 25-second chunk...');

    timeoutRef.current = window.setTimeout(() => {
      if (rec.state === 'recording') {
        rec.stop();
      }
    }, RECORDING_CHUNK_MS);
  };

  const start = async () => {
    if (!enabled) return;

    if (!navigator?.mediaDevices?.getUserMedia) {
      setStatus('Recording is not supported in this browser.');
      return;
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;
    shouldContinueRef.current = true;
    setRecording(true);

    recordOneCompleteChunk();
  };

  const stop = () => {
    shouldContinueRef.current = false;
    setRecording(false);
    setStatus('Stopped.');

    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
    }

    if (recRef.current && recRef.current.state !== 'inactive') {
      recRef.current.stop();
    }

    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  if (!enabled) {
    return <div>Recording unavailable until session exists.</div>;
  }

  return (
    <div className="row">
      <button onClick={start} disabled={recording}>
        Start recording
      </button>
      <button onClick={stop} disabled={!recording}>
        Stop recording
      </button>
      <span>{status}</span>
    </div>
  );
}