"""Workflow orchestration for the multi-agent purchasing assistant."""

from __future__ import annotations

from dataclasses import dataclass

from purchase_agent.adapters import (
    DryRunPurchaseExecutor,
    EmailGateway,
    MockCatalogResearchProvider,
    PurchaseExecutor,
    ResearchProvider,
)
from purchase_agent.agents import (
    ConfirmationAgent,
    IntakeAgent,
    PostPurchaseAgent,
    PurchaseExecutionAgent,
    RecommendationAgent,
    ResearchAgent,
)
from purchase_agent.models import (
    EmailMessage,
    PurchaseReceipt,
    PurchaseRecommendation,
    PurchaseRequest,
    ResearchReport,
    WorkflowStatus,
)


@dataclass(frozen=True)
class PendingPurchase:
    """Prepared purchase that is waiting for explicit user approval."""

    request: PurchaseRequest
    research_report: ResearchReport
    recommendation: PurchaseRecommendation
    approval_token: str
    confirmation_email: EmailMessage
    status: WorkflowStatus = WorkflowStatus.AWAITING_CONFIRMATION


@dataclass(frozen=True)
class PurchaseOutcome:
    """Completed purchase workflow result."""

    pending_purchase: PendingPurchase
    receipt: PurchaseReceipt
    receipt_email: EmailMessage
    status: WorkflowStatus = WorkflowStatus.PURCHASED


@dataclass
class AutonomousPurchaseWorkflow:
    """Coordinates specialized agents into a safe purchase workflow."""

    intake_agent: IntakeAgent
    research_agent: ResearchAgent
    recommendation_agent: RecommendationAgent
    confirmation_agent: ConfirmationAgent
    purchase_agent: PurchaseExecutionAgent
    post_purchase_agent: PostPurchaseAgent

    @classmethod
    def with_defaults(
        cls,
        email_gateway: EmailGateway,
        research_provider: ResearchProvider | None = None,
        purchase_executor: PurchaseExecutor | None = None,
    ) -> "AutonomousPurchaseWorkflow":
        """Create a workflow with safe development defaults."""

        return cls(
            intake_agent=IntakeAgent(),
            research_agent=ResearchAgent(research_provider or MockCatalogResearchProvider()),
            recommendation_agent=RecommendationAgent(),
            confirmation_agent=ConfirmationAgent(email_gateway),
            purchase_agent=PurchaseExecutionAgent(purchase_executor or DryRunPurchaseExecutor()),
            post_purchase_agent=PostPurchaseAgent(email_gateway),
        )

    def prepare_purchase(self, request: PurchaseRequest) -> PendingPurchase:
        """Research, recommend, and email a confirmation request."""

        validated_request = self.intake_agent.validate(request)
        research_report = self.research_agent.research(validated_request)
        recommendation = self.recommendation_agent.recommend(research_report)
        approval_token, confirmation_email = self.confirmation_agent.request_confirmation(
            validated_request, recommendation
        )

        return PendingPurchase(
            request=validated_request,
            research_report=research_report,
            recommendation=recommendation,
            approval_token=approval_token,
            confirmation_email=confirmation_email,
        )

    def confirm_and_purchase(
        self, pending_purchase: PendingPurchase, approval_token: str
    ) -> PurchaseOutcome:
        """Execute an approved purchase and send the post-purchase email."""

        receipt = self.purchase_agent.purchase(
            pending_purchase.request,
            pending_purchase.recommendation,
            expected_approval_token=pending_purchase.approval_token,
            provided_approval_token=approval_token,
        )
        receipt_email = self.post_purchase_agent.send_receipt(pending_purchase.request, receipt)
        return PurchaseOutcome(
            pending_purchase=pending_purchase,
            receipt=receipt,
            receipt_email=receipt_email,
        )
