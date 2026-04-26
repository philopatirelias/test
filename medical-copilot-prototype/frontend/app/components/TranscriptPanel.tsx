export default function TranscriptPanel({transcript}:{transcript:string}) {
  return <div className="panel"><h3>Transcript</h3>{transcript?<pre>{transcript}</pre>:<p>No transcript yet.</p>}</div>;
}
