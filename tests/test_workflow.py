from __future__ import annotations

import unittest
from decimal import Decimal

from purchase_agent.adapters import InMemoryEmailGateway, MockCatalogResearchProvider
from purchase_agent.agents import NoCandidateFoundError, PurchaseNotApprovedError
from purchase_agent.models import ProductCandidate, PurchaseRequest
from purchase_agent.workflow import AutonomousPurchaseWorkflow


class PurchaseWorkflowTest(unittest.TestCase):
    def test_confirmation_email_is_sent_before_purchase(self) -> None:
        email_gateway = InMemoryEmailGateway()
        workflow = AutonomousPurchaseWorkflow.with_defaults(email_gateway=email_gateway)
        request = PurchaseRequest(
            product_prompt="noise cancelling headphones",
            price_min=Decimal("100"),
            price_max=Decimal("200"),
            confirmation_email="buyer@example.com",
        )

        pending = workflow.prepare_purchase(request)

        self.assertEqual(len(email_gateway.sent_messages), 1)
        self.assertIn("Approval token:", email_gateway.sent_messages[0].body)
        self.assertEqual(pending.recommendation.candidate.name, "Northstar Noise Cancelling Headphones")

    def test_purchase_requires_matching_approval_token(self) -> None:
        email_gateway = InMemoryEmailGateway()
        workflow = AutonomousPurchaseWorkflow.with_defaults(email_gateway=email_gateway)
        request = PurchaseRequest(
            product_prompt="coffee maker",
            price_min=Decimal("50"),
            price_max=Decimal("100"),
            confirmation_email="buyer@example.com",
        )
        pending = workflow.prepare_purchase(request)

        with self.assertRaises(PurchaseNotApprovedError):
            workflow.confirm_and_purchase(pending, "wrong-token")

        self.assertEqual(len(email_gateway.sent_messages), 1)

    def test_purchase_sends_receipt_after_approval(self) -> None:
        email_gateway = InMemoryEmailGateway()
        workflow = AutonomousPurchaseWorkflow.with_defaults(email_gateway=email_gateway)
        request = PurchaseRequest(
            product_prompt="backpack",
            price_min=Decimal("40"),
            price_max=Decimal("80"),
            confirmation_email="buyer@example.com",
        )
        pending = workflow.prepare_purchase(request)

        outcome = workflow.confirm_and_purchase(pending, pending.approval_token)

        self.assertEqual(outcome.receipt.status, "simulated")
        self.assertEqual(len(email_gateway.sent_messages), 2)
        self.assertIn(outcome.receipt.order_id, email_gateway.sent_messages[1].body)

    def test_research_filters_out_items_above_budget(self) -> None:
        provider = MockCatalogResearchProvider(
            catalog=(
                ProductCandidate(
                    name="Budget Widget",
                    seller="Example",
                    price=Decimal("25"),
                    url="https://example.invalid/budget",
                    rating=4.1,
                    rationale="Cheap option.",
                ),
                ProductCandidate(
                    name="Premium Widget",
                    seller="Example",
                    price=Decimal("250"),
                    url="https://example.invalid/premium",
                    rating=4.9,
                    rationale="Expensive option.",
                ),
            )
        )
        workflow = AutonomousPurchaseWorkflow.with_defaults(
            email_gateway=InMemoryEmailGateway(), research_provider=provider
        )
        request = PurchaseRequest(
            product_prompt="widget",
            price_min=Decimal("10"),
            price_max=Decimal("100"),
            confirmation_email="buyer@example.com",
        )

        pending = workflow.prepare_purchase(request)

        self.assertEqual(pending.recommendation.candidate.name, "Budget Widget")
        self.assertEqual(len(pending.research_report.candidates), 1)

    def test_no_candidate_inside_price_range_fails_before_confirmation(self) -> None:
        email_gateway = InMemoryEmailGateway()
        workflow = AutonomousPurchaseWorkflow.with_defaults(email_gateway=email_gateway)
        request = PurchaseRequest(
            product_prompt="headphones",
            price_min=Decimal("1"),
            price_max=Decimal("25"),
            confirmation_email="buyer@example.com",
        )

        with self.assertRaises(NoCandidateFoundError):
            workflow.prepare_purchase(request)

        self.assertEqual(email_gateway.sent_messages, [])


if __name__ == "__main__":
    unittest.main()
