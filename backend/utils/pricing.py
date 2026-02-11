"""Shared pricing constants and margin computation logic."""

from __future__ import annotations

import math
from typing import Optional, Tuple

PRICE_THRESHOLDS = [15, 29, 49, 79, 99, 129, 149, 179, 209, 299, 499, 799, 999]
PRICE_MULTIPLIERS = [
    1.25,
    1.22,
    1.20,
    1.18,
    1.15,
    1.11,
    1.10,
    1.09,
    1.09,
    1.08,
    1.08,
    1.07,
    1.07,
    1.06,
]

COMMISSION_RATE = 0.045


def compute_margin_prices(
    price: float, tcp: float
) -> Tuple[float, float, float, float, float, Optional[float]]:
    """Compute margin-based prices from a base price and TCP value.

    Returns a tuple of:
        (margin45, price_with_tcp, price_with_margin, max_price, marge, marge_percent)
    """
    margin45 = price * COMMISSION_RATE
    price_with_tcp = price + tcp + margin45

    price_with_margin = price
    for threshold, multiplier in zip(PRICE_THRESHOLDS, PRICE_MULTIPLIERS):
        if price <= threshold:
            price_with_margin = price * multiplier
            break
    else:
        price_with_margin = price * PRICE_MULTIPLIERS[-1]

    if price > PRICE_THRESHOLDS[-1]:
        price_with_margin = price * PRICE_MULTIPLIERS[-1]

    max_price = math.ceil(max(price_with_tcp, price_with_margin))
    marge = max_price - tcp - price
    base_cost = price + tcp
    marge_percent = (marge / base_cost * 100) if base_cost else None
    return (
        round(margin45, 2),
        round(price_with_tcp, 2),
        round(price_with_margin, 2),
        max_price,
        round(marge, 2),
        round(marge_percent, 4) if marge_percent is not None else None,
    )
