"""External-service adapters used by the agent workflow.

The default adapters are safe for local development: they do not send real
email, browse the web, or place real orders. Production integrations should
implement the protocols below and keep the workflow's approval gate intact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from itertools import count
from typing import Protocol

from purchase_agent.models import EmailMessage, ProductCandidate, PurchaseReceipt, PurchaseRequest


class EmailGateway(Protocol):
    """Boundary for sending confirmation and receipt emails."""

    def send(self, message: EmailMessage) -> None:
        """Send an email message."""


class ResearchProvider(Protocol):
    """Boundary for product research."""

    def search(self, request: PurchaseRequest) -> tuple[ProductCandidate, ...]:
        """Return candidate products for the request."""


class PurchaseExecutor(Protocol):
    """Boundary for purchase execution."""

    def purchase(self, request: PurchaseRequest, candidate: ProductCandidate) -> PurchaseReceipt:
        """Purchase the selected product and return a receipt."""


@dataclass
class ConsoleEmailGateway:
    """Development email gateway that records messages and prints them."""

    sent_messages: list[EmailMessage] = field(default_factory=list)

    def send(self, message: EmailMessage) -> None:
        self.sent_messages.append(message)
        print(f"\n--- email to {message.to} ---")
        print(f"Subject: {message.subject}")
        print(message.body)
        print("--- end email ---\n")


@dataclass
class InMemoryEmailGateway:
    """Email gateway for tests or services that need to inspect sent messages."""

    sent_messages: list[EmailMessage] = field(default_factory=list)

    def send(self, message: EmailMessage) -> None:
        self.sent_messages.append(message)


@dataclass(frozen=True)
class MockCatalogResearchProvider:
    """Deterministic research provider for demos and tests."""

    catalog: tuple[ProductCandidate, ...] = (
        ProductCandidate(
            name="Acme QuietBrew Coffee Maker",
            seller="Example Home",
            price=Decimal("89.99"),
            url="https://example.invalid/products/acme-quietbrew",
            rating=4.5,
            rationale="Good reviews for reliability and quiet brewing.",
            attributes={"category": "coffee maker", "capacity": "12 cup"},
        ),
        ProductCandidate(
            name="Northstar Noise Cancelling Headphones",
            seller="Example Audio",
            price=Decimal("149.00"),
            url="https://example.invalid/products/northstar-headphones",
            rating=4.7,
            rationale="Strong active noise cancellation at a mid-range price.",
            attributes={"category": "headphones", "battery": "35 hours"},
        ),
        ProductCandidate(
            name="TrailLite Day Hiking Backpack",
            seller="Example Outdoors",
            price=Decimal("64.50"),
            url="https://example.invalid/products/traillite-backpack",
            rating=4.4,
            rationale="Lightweight, durable, and sized for day hikes.",
            attributes={"category": "backpack", "volume": "24L"},
        ),
    )

    def search(self, request: PurchaseRequest) -> tuple[ProductCandidate, ...]:
        prompt_terms = {
            term.strip().lower()
            for term in request.product_prompt.replace("-", " ").split()
            if len(term.strip()) > 2
        }

        matches: list[ProductCandidate] = []
        for item in self.catalog:
            searchable_text = " ".join(
                [item.name, item.seller, item.rationale, *item.attributes.values()]
            ).lower()
            if not prompt_terms or any(term in searchable_text for term in prompt_terms):
                matches.append(item)

        return tuple(matches or self.catalog)


@dataclass
class DryRunPurchaseExecutor:
    """Purchase executor that simulates an order without spending money."""

    _sequence: count = field(default_factory=lambda: count(1))

    def purchase(self, request: PurchaseRequest, candidate: ProductCandidate) -> PurchaseReceipt:
        order_number = next(self._sequence)
        return PurchaseReceipt(
            order_id=f"DRY-RUN-{order_number:06d}",
            candidate=candidate,
            total=candidate.price,
            currency=request.currency,
            status="simulated",
            post_purchase_message=(
                "Dry-run purchase completed. Replace DryRunPurchaseExecutor with a "
                "credentialed checkout adapter only after legal, fraud, payment, and "
                "user-consent controls are in place."
            ),
        )
