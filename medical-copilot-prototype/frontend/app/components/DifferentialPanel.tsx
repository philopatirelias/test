'use client';
import { useState } from 'react';
import { Differential } from '@/lib/types';

export default function DifferentialPanel({items}:{items:Differential[]}) {
  const [open, setOpen] = useState(false);
  const show = open ? items : items.slice(0,3);
  return <div className="panel"><h3>Possible differential hypotheses</h3>{show.length===0?<p>No differential hypotheses yet.</p>:show.map((d,i)=><div key={i}><strong>{d.rank}. {d.diagnosis}</strong><div>Supporting evidence: {d.supporting_evidence.join('; ')}</div><div>Missing information: {d.missing_information.join('; ')}</div></div>)}{items.length>3&&<button onClick={()=>setOpen(!open)}>{open?'Collapse':'Expand full list'}</button>}</div>;
}
