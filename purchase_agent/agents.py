"""Specialized agents that collaborate to complete a purchase workflow."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from secrets import token_urlsafe

from purchase_agent.adapters import EmailGateway, PurchaseExecutor, ResearchProvider
from purchase_agent.models import (
    EmailMessage,
    ProductCandidate,
    PurchaseReceipt,
    PurchaseRecommendation,
    PurchaseRequest,
    ResearchReport,
)


class PurchaseAgentError(ValueError):
    """Base exception for expected workflow failures."""


class InvalidPurchaseRequestError(PurchaseAgentError):
    """Raised when the user's request cannot be safely processed."""


class NoCandidateFoundError(PurchaseAgentError):
    """Raised when research found no products inside the requested price range."""


class PurchaseNotApprovedError(PurchaseAgentError):
    """Raised when purchase execution is attempted without approval."""


@dataclass(frozen=True)
class IntakeAgent:
    """Validates and normalizes a user's buying prompt."""

    def validate(self, request: PurchaseRequest) -> PurchaseRequest:
        product_prompt = request.product_prompt.strip()
        email = request.confirmation_email.strip()

        if not product_prompt:
            raise InvalidPurchaseRequestError("Product prompt is required.")
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise InvalidPurchaseRequestError("A valid confirmation email is required.")
        if request.price_min < Decimal("0"):
            raise InvalidPurchaseRequestError("Minimum price cannot be negative.")
        if request.price_max <= Decimal("0"):
            raise InvalidPurchaseRequestError("Maximum price must be greater than zero.")
        if request.price_min > request.price_max:
            raise InvalidPurchaseRequestError("Minimum price cannot exceed maximum price.")

        return PurchaseRequest(
            product_prompt=product_prompt,
            price_min=request.price_min,
            price_max=request.price_max,
            confirmation_email=email,
            currency=request.currency.upper(),
        )


@dataclass(frozen=True)
class ResearchAgent:
    """Finds candidate products and enforces the user's price range."""

    provider: ResearchProvider

    def research(self, request: PurchaseRequest) -> ResearchReport:
        candidates = tuple(
            candidate
            for candidate in self.provider.search(request)
            if request.price_min <= candidate.price <= request.price_max
        )
        notes = (
            f"Filtered candidates to {request.currency} {request.price_min} - {request.price_max}.",
        )
        return ResearchReport(request=request, candidates=candidates, notes=notes)


@dataclass(frozen=True)
class RecommendationAgent:
    """Selects the best candidate from a research report."""

    def recommend(self, report: ResearchReport) -> PurchaseRecommendation:
        if not report.candidates:
            raise NoCandidateFoundError(
                "No products matched the prompt inside the requested price range."
            )

        candidate = max(report.candidates, key=self._score_candidate)
        return PurchaseRecommendation(
            candidate=candidate,
            reason=(
                f"Selected {candidate.name} because it has a {candidate.rating:.1f}/5 "
                f"rating and fits the requested budget."
            ),
        )

    @staticmethod
    def _score_candidate(candidate: ProductCandidate) -> tuple[float, Decimal]:
        return (candidate.rating, -candidate.price)


@dataclass(frozen=True)
class ConfirmationAgent:
    """Sends the pre-purchase confirmation email."""

    email_gateway: EmailGateway

    def request_confirmation(
        self, request: PurchaseRequest, recommendation: PurchaseRecommendation
    ) -> tuple[str, EmailMessage]:
        approval_token = token_urlsafe(18)
        candidate = recommendation.candidate
        message = EmailMessage(
            to=request.confirmation_email,
            subject=f"Confirm purchase: {candidate.name}",
            body=(
                "Please confirm this purchase before the agent proceeds.\n\n"
                f"Requested item: {request.product_prompt}\n"
                f"Recommended product: {candidate.name}\n"
                f"Seller: {candidate.seller}\n"
                f"Price: {request.currency} {candidate.price}\n"
                f"Product URL: {candidate.url}\n"
                f"Reason: {recommendation.reason}\n\n"
                f"Approval token: {approval_token}\n\n"
                "Reply through the approved application flow with this token to authorize "
                "the purchase. Do not approve if any detail is wrong."
            ),
        )
        self.email_gateway.send(message)
        return approval_token, message


@dataclass(frozen=True)
class PurchaseExecutionAgent:
    """Executes an approved purchase through the configured adapter."""

    executor: PurchaseExecutor

    def purchase(
        self,
        request: PurchaseRequest,
        recommendation: PurchaseRecommendation,
        expected_approval_token: str,
        provided_approval_token: str,
    ) -> PurchaseReceipt:
        if not provided_approval_token or provided_approval_token != expected_approval_token:
            raise PurchaseNotApprovedError("Purchase requires the matching approval token.")
        return self.executor.purchase(request, recommendation.candidate)


@dataclass(frozen=True)
class PostPurchaseAgent:
    """Sends the post-purchase receipt email."""

    email_gateway: EmailGateway

    def send_receipt(self, request: PurchaseRequest, receipt: PurchaseReceipt) -> EmailMessage:
        message = EmailMessage(
            to=request.confirmation_email,
            subject=f"Purchase receipt: {receipt.candidate.name}",
            body=(
                "The approved purchase workflow has completed.\n\n"
                f"Order ID: {receipt.order_id}\n"
                f"Status: {receipt.status}\n"
                f"Product: {receipt.candidate.name}\n"
                f"Seller: {receipt.candidate.seller}\n"
                f"Total: {receipt.currency} {receipt.total}\n"
                f"Product URL: {receipt.candidate.url}\n\n"
                f"{receipt.post_purchase_message}"
            ),
        )
        self.email_gateway.send(message)
        return message
