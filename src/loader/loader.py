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
    k = int(k_decpre)
    return ScaleInfo(
        k_decpre=k,
        scale_factor_price=10**k / 10000.0,
        scale_factor_vol=float(10**k),
        price_tick_euros=0.01,
        price_tick_decpre=100.0 / 10**k,
    )


def reconstruct_lob(X: np.ndarray, k_decpre: int = 6) -> Lob:
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
    return Lob(Pa=Pa, Va=Va, Pb=Pb, Vb=Vb, Pa1=Pa1, Pb1=Pb1, M=M, S=S, Da=Da, Db=Db, OBI=OBI)


def find_stock_boundaries(m_series: np.ndarray, threshold: float = BOUNDARY_JUMP_EUR) -> list[int]:
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
    candidates = []
    root = (config.get("dataset") or {}).get("root")
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
        data_root = resolve_data_root(config or {})
    candidates = sorted(data_root.glob("Train*.txt"))
    if not candidates:
        raise FileNotFoundError(f"no training file in {data_root}")
    return candidates[0]


def load_train_lob(config: Mapping[str, Any]) -> tuple[np.ndarray, Lob, list[int]]:
    k = int((config.get("dataset") or {}).get("scale_exponent", 6))
    path = resolve_train_file(config)
    X, _ = load_fi2010_file(path)
    lob = reconstruct_lob(X, k_decpre=k)
    jumps = find_stock_boundaries(lob["M"])
    boundaries = segment_boundaries(jumps, len(lob["M"]))
    return X, lob, boundaries


def resolve_test_file(
    config: Mapping[str, Any] | None = None, day: int = 8, *, data_root: Path | None = None
) -> Path:
    if data_root is None:
        data_root = resolve_data_root(config or {})
    if day not in range(8, 11):
        raise ValueError(f"test day must be 8, 9, or 10, got {day}")
    cf_id = day - 1
    candidates = sorted(data_root.glob(f"Test*CF_{cf_id}.txt"))
    if not candidates:
        raise FileNotFoundError(f"no test file for day {day} in {data_root}")
    return candidates[0]


def load_test_lob(config: Mapping[str, Any], day: int) -> tuple[np.ndarray, Lob, list[int]]:
    k = int((config.get("dataset") or {}).get("scale_exponent", 6))
    path = resolve_test_file(config, day=day)
    X, _ = load_fi2010_file(path)
    lob = reconstruct_lob(X, k_decpre=k)
    return X, lob, [0, len(lob["M"])]


def split_row_ranges(start: int, end: int, num_days: int) -> list[tuple[int, int]]:
    length = (end - start) // num_days
    ranges = []
    for i in range(num_days):
        s = start + i * length
        e = start + (i + 1) * length if i < num_days - 1 else end
        ranges.append((s, e))
    return ranges


def load_day(stock: str, day: int) -> tuple[Lob, int, bool]:
    # Returns (lob_slice, day_index, is_measured_boundary)
    config = {}
    stock_idx = -1
    for i, name in enumerate(STOCK_NAMES):
        if stock in name:
            stock_idx = i
            break
    if stock_idx == -1:
        raise ValueError(f"unknown stock {stock!r}; expected one of {STOCK_NAMES}")

    if day <= 7:
        _, lob, boundaries = load_train_lob(config)
        if stock_idx >= len(boundaries) - 1:
            stock_idx = len(boundaries) - 2
        start = boundaries[stock_idx]
        end = boundaries[stock_idx + 1]
        ranges = split_row_ranges(start, end, 7)
        if day - 1 >= len(ranges):
            raise ValueError(f"Day {day} out of bounds")
        s, e = ranges[day - 1]
        lob_slice = {k: v[s:e] for k, v in lob.items()}
        return lob_slice, day, False
    else:
        _, lob, boundaries = load_test_lob(config, day)
        # Note: If test file has multiple stocks (which FI-2010 test files actually do!),
        # we still segment it based on mid price jumps
        jumps = find_stock_boundaries(lob["M"])
        test_bounds = segment_boundaries(jumps, len(lob["M"]))
        if stock_idx < len(test_bounds) - 1:
            s, e = test_bounds[stock_idx], test_bounds[stock_idx + 1]
            lob_slice = {k: v[s:e] for k, v in lob.items()}
        else:
            lob_slice = lob
        return lob_slice, day, True
