export default function StatusPill({priority}:{priority:'red'|'yellow'|'green'}) {
  return <span className={`pill ${priority}`}>{priority.toUpperCase()}</span>;
}
