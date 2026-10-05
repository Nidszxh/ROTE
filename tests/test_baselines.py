from __future__ import annotations

import numpy as np
import pytest

from src.benchmarks.baselines import depth_proportional_plan, twap_plan, vwap_proxy_plan
from src.utils.contracts import Order


def test_twap_plan_normal():
    order = Order(side="buy", size=1000.0, horizon=5, params={})
    schedule = twap_plan(order)
    assert len(schedule.shares) == 5
    np.testing.assert_allclose(schedule.shares, np.full(5, 200.0))
    np.testing.assert_allclose(np.sum(schedule.shares), 1000.0)


def test_twap_plan_single_step():
    order = Order(side="buy", size=50.0, horizon=1, params={})
    schedule = twap_plan(order)
    assert len(schedule.shares) == 1
    assert schedule.shares[0] == 50.0


def test_twap_plan_invalid_inputs():
    with pytest.raises(ValueError, match="Order size must be strictly positive"):
        twap_plan(Order(side="buy", size=0.0, horizon=5, params={}))

    with pytest.raises(ValueError, match="Order size must be strictly positive"):
        twap_plan(Order(side="buy", size=-100.0, horizon=5, params={}))

    with pytest.raises(ValueError, match="Order horizon must be strictly positive"):
        twap_plan(Order(side="buy", size=100.0, horizon=0, params={}))


def test_depth_proportional_plan_valid():
    order = Order(side="buy", size=600.0, horizon=3, params={})
    book = {"Da": np.array([100.0, 200.0, 300.0, 400.0])}
    schedule = depth_proportional_plan(order, book)

    # 100 / 600 * 600 = 100, 200, 300
    expected = np.array([100.0, 200.0, 300.0])
    np.testing.assert_allclose(schedule.shares, expected)
    np.testing.assert_allclose(np.sum(schedule.shares), 600.0)


def test_depth_proportional_plan_zero_depth_fallback():
    order = Order(side="buy", size=600.0, horizon=3, params={})
    book = {"Da": np.array([0.0, 0.0, 0.0])}
    schedule = depth_proportional_plan(order, book)
    # Should fall back cleanly to TWAP
    np.testing.assert_allclose(schedule.shares, np.full(3, 200.0))


def test_depth_proportional_plan_missing_keys_and_short():
    order = Order(side="buy", size=100.0, horizon=5, params={})
    with pytest.raises(KeyError, match="missing required depth key 'Da'"):
        depth_proportional_plan(order, {})

    with pytest.raises(ValueError, match="shorter than horizon"):
        depth_proportional_plan(order, {"Da": np.array([10.0, 20.0])})


def test_vwap_proxy_plan_valid():
    order = Order(side="buy", size=1000.0, horizon=2, params={})
    book = {
        "Da": np.array([100.0, 300.0]),
        "Db": np.array([100.0, 100.0]),
    }
    # step 0: Da / (Da + Db) = 100 / 200 = 0.5
    # step 1: Da / (Da + Db) = 300 / 400 = 0.75
    # sum = 1.25 -> step 0: 0.5/1.25 * 1000 = 400; step 1: 0.75/1.25 * 1000 = 600
    schedule = vwap_proxy_plan(order, book)
    np.testing.assert_allclose(schedule.shares, np.array([400.0, 600.0]))
    np.testing.assert_allclose(np.sum(schedule.shares), 1000.0)


def test_vwap_proxy_plan_fallback_and_validation():
    order = Order(side="buy", size=500.0, horizon=2, params={})
    with pytest.raises(KeyError):
        vwap_proxy_plan(order, {"Da": np.array([10.0, 20.0])})

    with pytest.raises(ValueError, match="shorter than the order horizon"):
        vwap_proxy_plan(order, {"Da": np.array([10.0]), "Db": np.array([10.0])})

    # Zero denominator fallback to TWAP
    book = {"Da": np.array([0.0, 0.0]), "Db": np.array([0.0, 0.0])}
    schedule = vwap_proxy_plan(order, book)
    np.testing.assert_allclose(schedule.shares, np.full(2, 250.0))
