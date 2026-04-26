import { Suggestion } from '@/lib/types';
import StatusPill from './StatusPill';

export default function SuggestionPanel({items}:{items:Suggestion[]}) {
  return <div className="panel"><h3>Live interview suggestions</h3>{items.length===0?<p>Analysis pending / no suggestions yet.</p>:items.map((s,i)=><div key={i} style={{borderBottom:'1px solid #eee',padding:'8px 0'}}><StatusPill priority={s.priority}/><div><strong>{s.question}</strong></div><div>{s.reason}</div>{s.answer_found&&<div>answer_found: {s.answer_found}</div>}</div>)}</div>;
}
