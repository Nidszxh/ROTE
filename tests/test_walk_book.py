import pytest

from cost.walk_book import walk_book_buy

pytestmark = pytest.mark.T10


def test_zero_shares():
    res = walk_book_buy([100.0], [10.0], 0.0)
    assert res["shares_filled"] == 0.0
    assert res["cash_paid"] == 0.0
    assert res["unfilled_shares"] == 0.0


def test_zero_shares_empty_book():
    res = walk_book_buy([], [], 0.0)
    assert res["shares_filled"] == 0.0


def test_negative_shares_raises():
    with pytest.raises(ValueError):
        walk_book_buy([100.0], [10.0], -1.0)


def test_empty_book_with_shares_raises():
    with pytest.raises(ValueError):
        walk_book_buy([], [], 5.0)


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        walk_book_buy([100.0, 101.0], [10.0], 5.0)


def test_negative_volume_raises():
    with pytest.raises(ValueError):
        walk_book_buy([100.0], [-5.0], 1.0)


def test_footprint_reduces_volume():
    res = walk_book_buy([100.0], [10.0], 6.0, footprint=4.0)
    assert res["shares_filled"] == 6.0
    assert res["cash_paid"] == 600.0


def test_partial_fill():
    res = walk_book_buy([100.0, 101.0], [5.0, 5.0], 12.0)
    assert res["shares_filled"] == 10.0
    assert res["unfilled_shares"] == 2.0


def test_mid_price_none_half_spread():
    res = walk_book_buy([100.0], [10.0], 5.0, mid_price=None)
    assert res["half_spread_cost"] == 0.0
    assert res["walk_premium"] == 0.0


def test_t10_worked_example():
    ask_prices = [100.00, 100.05, 100.10]
    ask_volumes = [800.0, 1200.0, 2500.0]
    res = walk_book_buy(ask_prices, ask_volumes, 2000.0, mid_price=99.975)
    assert res["shares_filled"] == pytest.approx(2000.0, abs=1e-8)
    assert res["cash_paid"] == pytest.approx(800.0 * 100.00 + 1200.0 * 100.05, abs=1e-6)
    assert res["half_spread_cost"] == pytest.approx(2000.0 * (100.00 - 99.975), abs=1e-6)
    assert res["shortfall_bps"] == pytest.approx(5.501, abs=0.05)
