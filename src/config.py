"""Experiment configuration loading and hashing."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "experiment.yaml"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def require(cfg: Mapping[str, Any], *keys: str) -> Any:
    cur = cfg
    for key in keys:
        if isinstance(cur, Mapping) and key in cur:
            cur = cur[key]
        else:
            raise ValueError(f"missing config key: {'.'.join(keys[: keys.index(key) + 1])}")
    return cur


def _canonical_sha256(cfg: Mapping[str, Any]) -> str:
    dumped = yaml.safe_dump({k: v for k, v in cfg.items() if not k.startswith("_")}, sort_keys=True)
    return hashlib.sha256(dumped.encode()).hexdigest()


def load(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"config file not found: {p}")
    with p.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"config root must be a mapping, got {type(raw).__name__}")
    for sec in ("dataset", "audit", "period"):
        if sec not in raw or not isinstance(raw[sec], dict):
            raise ValueError(f"config missing required section(s): {sec}")
    cfg = dict(raw)
    cfg["_sha256"] = _canonical_sha256(cfg)
    proposal_path = (
        REPO_ROOT / require(cfg, "proposal", "path")
        if cfg.get("proposal")
        else REPO_ROOT / "PROPOSAL.md"
    )
    try:
        cfg["_proposal_sha256"] = sha256_file(proposal_path)
    except OSError as exc:
        logger.warning("cannot hash %s: %s", proposal_path, exc)
        cfg["_proposal_sha256"] = None
    return cfg


def sha256(cfg: dict[str, Any] | None = None) -> str:
    if cfg is None:
        cfg = load()
    return cfg.get("_sha256", "")
