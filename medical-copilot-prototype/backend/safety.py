import re
from typing import Iterable

FORBIDDEN_PATTERNS = [
    r"\bthe patient has\b",
    r"\bthis is definitely\b",
    r"\bno further assessment needed\b",
    r"\bstart medication\b",
    r"\bprescribe\b",
]
FORBIDDEN_PII_TERMS = [
    "name",
    "date of birth",
    "address",
    "phone",
    "email",
    "insurance",
    "national identifier",
]


def contains_forbidden_language(text: str) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in FORBIDDEN_PATTERNS)


def contains_phi_request(text: str) -> bool:
    low = text.lower()
    return any(term in low for term in FORBIDDEN_PII_TERMS)


def check_strings(texts: Iterable[str]) -> None:
    for t in texts:
        if contains_forbidden_language(t):
            raise ValueError("Forbidden overconfident or treatment language detected")
        if contains_phi_request(t):
            raise ValueError("Forbidden patient-identifying request detected")
