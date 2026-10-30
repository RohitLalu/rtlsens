from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_names(p) -> list[str]:
    """Read a whitespace/newline separated list of problem names."""
    return Path(p).read_text().split()
