export default function ConsultSelector({value, onChange}:{value:string; onChange:(v:string)=>void}) {
  const options = ['internal_medicine','cardiology','gastroenterology','neurology','general_practice','emergency_triage'];
  return <select value={value} onChange={e=>onChange(e.target.value)}>{options.map(o=><option key={o} value={o}>{o}</option>)}</select>;
}
