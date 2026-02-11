"""Tests for utils/pricing.py – compute_margin_prices."""

import math
from utils.pricing import (
    COMMISSION_RATE,
    PRICE_MULTIPLIERS,
    PRICE_THRESHOLDS,
    compute_margin_prices,
)


def test_commission_rate_value():
    assert COMMISSION_RATE == 0.045


def test_thresholds_and_multipliers_same_length_plus_one():
    assert len(PRICE_MULTIPLIERS) == len(PRICE_THRESHOLDS) + 1


def test_price_zero():
    margin45, ptcp, pmarg, maxp, marge, mpct = compute_margin_prices(0, 0)
    assert margin45 == 0
    assert ptcp == 0
    assert pmarg == 0
    assert maxp == 0
    assert marge == 0
    assert mpct is None  # base_cost = 0


def test_price_in_first_threshold():
    price, tcp = 10.0, 5.0
    margin45, ptcp, pmarg, maxp, marge, mpct = compute_margin_prices(price, tcp)
    assert margin45 == round(price * COMMISSION_RATE, 2)
    assert ptcp == round(price + tcp + margin45, 2)
    assert pmarg == round(price * 1.25, 2)
    expected_max = math.ceil(max(ptcp, pmarg))
    assert maxp == expected_max
    assert marge == round(maxp - tcp - price, 2)


def test_price_exactly_at_threshold():
    price, tcp = 15.0, 0.0
    margin45, ptcp, pmarg, maxp, marge, mpct = compute_margin_prices(price, tcp)
    # price <= 15 → multiplier 1.25
    assert pmarg == round(15.0 * 1.25, 2)


def test_price_above_first_threshold():
    price, tcp = 20.0, 2.0
    margin45, ptcp, pmarg, maxp, marge, mpct = compute_margin_prices(price, tcp)
    # 15 < 20 <= 29 → multiplier 1.22
    assert pmarg == round(20.0 * 1.22, 2)


def test_price_above_last_threshold():
    price, tcp = 1500.0, 14.0
    margin45, ptcp, pmarg, maxp, marge, mpct = compute_margin_prices(price, tcp)
    assert pmarg == round(1500.0 * PRICE_MULTIPLIERS[-1], 2)


def test_marge_percent_calculated():
    price, tcp = 100.0, 10.0
    _, _, _, maxp, marge, mpct = compute_margin_prices(price, tcp)
    expected = round((marge / (price + tcp)) * 100, 4)
    assert mpct == expected


def test_marge_percent_none_when_base_zero():
    _, _, _, _, _, mpct = compute_margin_prices(0, 0)
    assert mpct is None


def test_max_price_is_ceiling():
    price, tcp = 50.5, 3.0
    _, ptcp, pmarg, maxp, _, _ = compute_margin_prices(price, tcp)
    assert maxp == math.ceil(max(ptcp, pmarg))
    assert isinstance(maxp, int)


def test_return_tuple_length():
    result = compute_margin_prices(100, 10)
    assert len(result) == 6


def test_all_thresholds_produce_correct_multiplier():
    """Iterate every threshold boundary to ensure correct multiplier."""
    for i, threshold in enumerate(PRICE_THRESHOLDS):
        _, _, pmarg, _, _, _ = compute_margin_prices(threshold, 0)
        assert pmarg == round(threshold * PRICE_MULTIPLIERS[i], 2), (
            f"Threshold {threshold} should use multiplier {PRICE_MULTIPLIERS[i]}"
        )
