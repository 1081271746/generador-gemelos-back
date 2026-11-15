"""Conservative offline gate; not a substitute for legal/privacy review."""
import re

PATTERNS = [
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:api[_-]?key|password|contraseña|authorization)\s*[:=]\s*\S+", re.I),
    re.compile(r"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
]


def check_privacy(text):
    if any(pattern.search(text) for pattern in PATTERNS):
        raise ValueError("Possible personal data or credentials: redact and revalidate offline")
