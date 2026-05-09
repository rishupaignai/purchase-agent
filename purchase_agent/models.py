"""Shared data models for the purchasing assistant."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Mapping


class WorkflowStatus(str, Enum):
    """High-level purchase workflow states."""

    AWAITING_CONFIRMATION = "awaiting_confirmation"
    PURCHASED = "purchased"


@dataclass(frozen=True)
class PurchaseRequest:
    """A user's purchasing intent and guardrails."""

    product_prompt: str
    price_min: Decimal
    price_max: Decimal
    confirmation_email: str
    currency: str = "USD"


@dataclass(frozen=True)
class ProductCandidate:
    """One researched product option."""

    name: str
    seller: str
    price: Decimal
    url: str
    rating: float
    rationale: str
    attributes: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ResearchReport:
    """Research output that can be audited before purchase."""

    request: PurchaseRequest
    candidates: tuple[ProductCandidate, ...]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PurchaseRecommendation:
    """Decision-agent recommendation."""

    candidate: ProductCandidate
    reason: str


@dataclass(frozen=True)
class EmailMessage:
    """A sent or sendable email message."""

    to: str
    subject: str
    body: str


@dataclass(frozen=True)
class PurchaseReceipt:
    """Result returned by a purchase executor."""

    order_id: str
    candidate: ProductCandidate
    total: Decimal
    currency: str
    status: str
    post_purchase_message: str
