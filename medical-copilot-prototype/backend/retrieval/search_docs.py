from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DOCS = BASE / "documents"


def search_relevant_snippets(consult_type: str, transcript: str, top_k: int = 3) -> list[str]:
    path = DOCS / f"{consult_type}.md"
    if not path.exists():
        path = DOCS / "general_practice.md"
    text = path.read_text(encoding="utf-8")
    sections = [s.strip() for s in text.split("##") if s.strip()]
    terms = set(transcript.lower().split())

    def score(section: str) -> int:
        words = set(section.lower().split())
        base = len(terms & words)
        if "red flag" in section.lower() or "safety" in section.lower():
            base += 10
        return base

    ranked = sorted(sections, key=score, reverse=True)
    return ranked[:top_k]
