export default function DeleteSessionButton({onDelete, disabled}:{onDelete:()=>void; disabled:boolean}) {
  return <button disabled={disabled} onClick={onDelete}>Delete session</button>;
}
