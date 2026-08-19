"""
Agent 1 - Logistics & Freshness Assessment
Rule-based severity classifier.

Given a shipment delay and the product's remaining shelf life (or quality
tolerance, for non-perishables like wheat), this calculates a "buffer" and
classifies the disruption as LOW, MEDIUM, or HIGH severity.

This is intentionally rule-based (not LLM-driven) so severity decisions
stay transparent and auditable. The LLM layer gets added later, on top of
this, to explain the result in natural language.
"""

from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class DisruptionEvent:
    shipment_id: str
    product: str
    delay_days: float
    remaining_shelf_life_days: float  # for wheat: remaining quality/storage tolerance
    requested_delivery_days_from_now: float  # how soon the customer needs it


@dataclass
class SeverityResult:
    shipment_id: str
    buffer_days: float
    severity: Severity
    explanation: str


def classify_severity(event: DisruptionEvent) -> SeverityResult:
    """
    Core rule: buffer = remaining shelf life - delay length.
    A large positive buffer -> LOW severity.
    A small or borderline buffer -> MEDIUM severity (needs Agent 2's help).
    A negative buffer -> HIGH severity (real risk of loss/stockout).
    """
    buffer_days = event.remaining_shelf_life_days - event.delay_days

    if buffer_days >= 3:
        severity = Severity.LOW
        explanation = (
            f"Delay of {event.delay_days} days is comfortably covered by "
            f"{event.remaining_shelf_life_days} days of remaining shelf life. "
            f"No action required."
        )
    elif 0 <= buffer_days < 3:
        severity = Severity.MEDIUM
        explanation = (
            f"Delay of {event.delay_days} days leaves only {buffer_days} days "
            f"of buffer. Risk of spoilage/stockout before replenishment. "
            f"Recommend checking alternative stock coverage."
        )
    else:
        severity = Severity.HIGH
        explanation = (
            f"Delay of {event.delay_days} days exceeds remaining shelf life "
            f"by {abs(buffer_days)} days. High risk of loss. "
            f"Recovery plan required."
        )

    return SeverityResult(
        shipment_id=event.shipment_id,
        buffer_days=buffer_days,
        severity=severity,
        explanation=explanation,
    )


if __name__ == "__main__":
    # Quick manual tests with made-up values, no real data needed yet.
    test_events = [
        DisruptionEvent("SHIP-001", "Strawberries", delay_days=1, remaining_shelf_life_days=5, requested_delivery_days_from_now=2),
        DisruptionEvent("SHIP-002", "Strawberries", delay_days=4, remaining_shelf_life_days=5, requested_delivery_days_from_now=2),
        DisruptionEvent("SHIP-003", "Wheat", delay_days=60, remaining_shelf_life_days=10, requested_delivery_days_from_now=30),
    ]

    for event in test_events:
        result = classify_severity(event)
        print(f"\n--- {result.shipment_id} ---")
        print(f"Severity: {result.severity.value}")
        print(f"Buffer: {result.buffer_days} days")
        print(f"Explanation: {result.explanation}")