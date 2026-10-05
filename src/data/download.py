"""Dataset acquisition helpers for FI-2010.

FI-2010 is not redistributed here. This module documents credible sources
and provides a stub that records the chosen file in data/README.md per A0.
See PROPOSAL.md section 4.1 and data/README.md.
"""

import os
from pathlib import Path

CREDIBLE_SOURCES = [
    "https://github.com/VPeterV/fi2010",  # common reference
    "https://etsin.fairdata.fi/dataset/6aa3ad3c-15ad-421f-bbd0-c44c2a0f66c2",  # FI-2010
]


def ensure_dataset(root: str | None = None) -> Path:
    root = Path(root or os.environ.get("ROTE_DATA_ROOT", "data/raw")).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    (root / ".gitkeep").touch(exist_ok=True)
    return root


if __name__ == "__main__":
    path = ensure_dataset()
    print(f"Dataset directory ensured at: {path}")
