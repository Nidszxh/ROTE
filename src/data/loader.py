"""FI-2010 dataset loading, scale recovery, and LOB reconstruction."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TypedDict

import numpy as np

N_FEATURES = 144
N_LABELS = 5
N_ROWS = N_FEATURES + N_LABELS
LOB_LEVELS = 10
BOUNDARY_JUMP_EUR = 1.0

STOCK_NAMES = [
    "Kesko (KESBV)",
    "Outokumpu (OUT1V)",
    "Sampo (SAMPO)",
    "Rautaruukki (RTRKS)",
    "Wärtsilä (WRT1V)",
]


class FileMeta(TypedDict):
    path: str
    n_rows: int
    n_features: int
    n_labels: int
    n_samples: int
    shape: tuple[int, int]


class ScaleInfo(TypedDict):
    k_decpre: int
    scale_factor_price: float
    scale_factor_vol: float
    price_tick_euros: float
    price_tick_decpre: float


class Lob(TypedDict):
    Pa: np.ndarray
    Va: np.ndarray
    Pb: np.ndarray
    Vb: np.ndarray
    Pa1: np.ndarray
    Pb1: np.ndarray
    M: np.ndarray
    S: np.ndarray
    Da: np.ndarray
    Db: np.ndarray
    OBI: np.ndarray


class ScaleDetection(TypedDict):
    k_decpre: int | None


def stock_name(i: int) -> str:
    if i < 0 or i >= len(STOCK_NAMES):
        return f"Stock block {i + 1}"
    return STOCK_NAMES[i]


def stock_short_name(i: int) -> str:
    name = stock_name(i)
    try:
        return name.split()[0]
    except Exception:
        return name


def load_fi2010_file(path: str | Path) -> tuple[np.ndarray, FileMeta]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"FI-2010 file not found: {p}")
    rows = []
    expected = None
    with p.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            s = line.rstrip()
            if not s.strip():
                continue
            tokens = s.split()
            if expected is None:
                expected = len(tokens)
            elif len(tokens) != expected:
                raise ValueError(
                    f"{p.name}: row {lineno} has {len(tokens)} values, expected {expected}"
                )
            try:
                rows.append(np.array(tokens, dtype=np.float64))
            except ValueError as exc:
                raise ValueError(f"{p.name}: row {lineno}: {exc}") from exc
    if len(rows) != N_ROWS:
        raise ValueError(f"{p.name}: expected {N_ROWS} rows (features + labels), got {len(rows)}")
    feature_rows = rows[:N_FEATURES]
    data = np.vstack(feature_rows)
    X = data.T
    meta: FileMeta = {
        "path": str(p),
        "n_rows": N_ROWS,
        "n_features": N_FEATURES,
        "n_labels": N_LABELS,
        "n_samples": int(X.shape[0]),
        "shape": tuple(X.shape),
    }
    return X, meta


def recover_scale(k_decpre: int = 6) -> ScaleInfo:
    if k_decpre < 0:
        raise ValueError(f"k_decpre must be non-negative, got {k_decpre}")
    k = int(k_decpre)
    return ScaleInfo(
        k_decpre=k,
        scale_factor_price=10**k / 10000.0,
        scale_factor_vol=float(10**k),
        price_tick_euros=0.01,
        price_tick_decpre=100.0 / 10**k,
    )


def reconstruct_lob(X: np.ndarray, k_decpre: int = 6) -> Lob:
    if not isinstance(X, np.ndarray) or X.ndim != 2:
        raise ValueError(f"expected 2-D feature matrix, got shape {getattr(X, 'shape', 'unknown')}")
    if X.shape[1] < N_FEATURES:
        raise ValueError(f"expected at least {N_FEATURES} feature columns, got {X.shape[1]}")
    n_samples = X.shape[0]
    scale = recover_scale(k_decpre)
    levels = X[:, : LOB_LEVELS * 4]
    Pa = levels[:, 0::4] * scale["scale_factor_price"]
    Va = levels[:, 1::4] * scale["scale_factor_vol"]
    Pb = levels[:, 2::4] * scale["scale_factor_price"]
    Vb = levels[:, 3::4] * scale["scale_factor_vol"]
    Pa1 = Pa[:, 0]
    Pb1 = Pb[:, 0]
    M = (Pa1 + Pb1) / 2.0
    S = Pa1 - Pb1
    Da = Va.sum(axis=1)
    Db = Vb.sum(axis=1)
    denom = Da + Db
    OBI = np.zeros(n_samples)
    mask = denom > 0
    OBI[mask] = (Db[mask] - Da[mask]) / denom[mask]
    return Lob(
        Pa=Pa,
        Va=Va,
        Pb=Pb,
        Vb=Vb,
        Pa1=Pa1,
        Pb1=Pb1,
        M=M,
        S=S,
        Da=Da,
        Db=Db,
        OBI=OBI,
    )


def find_stock_boundaries(m_series: np.ndarray, threshold: float = BOUNDARY_JUMP_EUR) -> list[int]:
    if not isinstance(m_series, np.ndarray) or m_series.ndim != 1:
        raise ValueError(
            f"expected 1-D mid-price series, got shape {getattr(m_series, 'shape', 'unknown')}"
        )
    if len(m_series) < 2:
        return []
    diffs = np.abs(np.diff(m_series))
    jumps = np.where(diffs > threshold)[0]
    return jumps.tolist()


def segment_boundaries(jumps: Sequence[int], n_samples: int) -> list[int]:
    edges = [0]
    for j in jumps:
        edge = int(j) + 1
        if edges[-1] < edge < n_samples:
            edges.append(edge)
    if edges[-1] < n_samples:
        edges.append(n_samples)
    return edges


def resolve_data_root(config: Mapping[str, Any]) -> Path:
    candidates: list[Path] = []
    dataset = config.get("dataset") or {}
    root = dataset.get("root")
    if root:
        candidates.append(Path(root))
    env = os.environ.get("ROTE_DATA_ROOT")
    if env:
        candidates.append(Path(env))
    candidates.append(Path("data/raw/FI-2010"))
    candidates.append(Path("data/FI-2010"))
    for c in candidates:
        if c.is_dir():
            return c
    tried = ", ".join(map(str, candidates))
    raise FileNotFoundError(f"no FI-2010 data directory found; tried: {tried}")


def resolve_train_file(
    config: Mapping[str, Any] | None = None, *, data_root: Path | None = None
) -> Path:
    if data_root is None:
        if config is None:
            raise ValueError("config required when data_root not provided")
        data_root = resolve_data_root(config)
    if config is not None:
        preferred = (config.get("dataset") or {}).get("file")
        if preferred:
            p = data_root / preferred
            if p.is_file():
                return p
    candidates = sorted(data_root.glob("Train*.txt"))
    if not candidates:
        raise FileNotFoundError(f"no training file matching 'Train*.txt' in {data_root}")
    return candidates[0]


def load_train_lob(config: Mapping[str, Any]) -> tuple[np.ndarray, Lob, list[int]]:
    k = int((config.get("dataset") or {}).get("scale_exponent", 6))
    path = resolve_train_file(config)
    X, _ = load_fi2010_file(path)
    lob = reconstruct_lob(X, k_decpre=k)
    jumps = find_stock_boundaries(lob["M"])
    boundaries = segment_boundaries(jumps, len(lob["M"]))
    return X, lob, boundaries


def period_log_returns(m_series: np.ndarray, rows_per_period: int) -> np.ndarray:
    if not isinstance(m_series, np.ndarray) or m_series.ndim != 1:
        return np.array([], dtype=float)
    if rows_per_period <= 1:
        return np.array([], dtype=float)
    n = len(m_series)
    if n < 2 * rows_per_period:
        return np.array([], dtype=float)
    n_periods = n // rows_per_period
    end = n_periods * rows_per_period
    period_mids = m_series[:end].reshape(n_periods, rows_per_period)[:, -1]
    if len(period_mids) < 2:
        return np.array([], dtype=float)
    return np.diff(np.log(period_mids))


def sigma_min_floor(returns: np.ndarray) -> float:
    if not isinstance(returns, np.ndarray) or returns.size == 0:
        return 0.0
    magnitudes = np.abs(returns)
    nonzero = magnitudes[magnitudes > 1e-7]
    if nonzero.size == 0:
        return 0.0
    return float(np.percentile(nonzero, 10.0))
