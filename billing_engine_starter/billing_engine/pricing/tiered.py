"""
TieredPricing — different price per unit depending on the tier the quantity falls into.

This is the "cumulative" / "stacked" tier model, NOT the "volume" model:
    Tiers: [(0, 1000, ₹2.00), (1000, 5000, ₹1.50), (5000, None, ₹1.00)]
    Quantity = 6000:
        First 1000 units  @ ₹2.00 = ₹2000
        Next  4000 units  @ ₹1.50 = ₹6000
        Last  1000 units  @ ₹1.00 = ₹1000
        ------------------------------------
        Total                     = ₹9000

A tier with `to_units = None` is the open-ended top tier.

Tier boundaries are HALF-OPEN on the right: a tier (from, to, price)
covers units strictly less than `to` (i.e. [from, to)).
"""

from dataclasses import dataclass
from typing import Optional

from billing_engine.money import Money
from billing_engine.pricing.base import PricingStrategy


@dataclass(frozen=True)
class Tier:
    from_units: int
    to_units: Optional[int]   # None = open-ended top tier
    unit_price: Money


class TieredPricing(PricingStrategy):
    """Charges across multiple price tiers based on cumulative quantity."""

    def __init__(self, tiers: list[Tier]) -> None:
        if not tiers:
            raise ValueError("tiers list cannot be empty")

        currency = tiers[0].unit_price.currency
        open_ended_count = 0

        for i, tier in enumerate(tiers):
            # currency check
            if tier.unit_price.currency != currency:
                raise ValueError("All tiers must use the same currency")

            # track open-ended tiers
            if tier.to_units is None:
                open_ended_count += 1
                if i != len(tiers) - 1:
                    raise ValueError("Only last tier can be open-ended")

            # contiguity
            if i > 0:
                prev = tiers[i - 1]
                if prev.to_units != tier.from_units:
                    raise ValueError("Tiers must be contiguous")

        # MUST have exactly one open-ended tier
        if open_ended_count != 1:
            raise ValueError("Top tier must be open-ended (to_units=None)")

        # AND last tier must be open-ended
        if tiers[-1].to_units is not None:
            raise ValueError("Top tier must be open-ended (to_units=None)")

        self.tier = tiers

    def calculate(self, quantity: int) -> Money:
        # 1. Reject negative quantity
        if quantity < 0:
            raise ValueError("quantity cannot be negative")

        currency = self.tier[0].unit_price.currency
        total = Money.zero(currency)

        for tier in self.tier:
            # skip if quantity is below tier start
            if quantity <= tier.from_units:
                continue

            # 2. open-ended tier
            if tier.to_units is None:
                units = quantity - tier.from_units
            else:
                units = min(quantity, tier.to_units) - tier.from_units

            # 3. safety
            if units > 0:
                total += tier.unit_price * units

        return total
    