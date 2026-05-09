"""Command-line demo for the multi-agent purchase workflow."""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation

from purchase_agent.adapters import ConsoleEmailGateway
from purchase_agent.agents import PurchaseAgentError
from purchase_agent.models import PurchaseRequest
from purchase_agent.workflow import AutonomousPurchaseWorkflow


def _money(value: str) -> Decimal:
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not a valid amount") from exc
    if amount < Decimal("0"):
        raise argparse.ArgumentTypeError("amount must be non-negative")
    return amount


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a safe dry-run demo of the multi-agent purchasing assistant."
    )
    parser.add_argument("product_prompt", help="What you want the agent to buy.")
    parser.add_argument("--min-price", type=_money, default=Decimal("0.00"))
    parser.add_argument("--max-price", type=_money, required=True)
    parser.add_argument("--email", required=True, help="Address for confirmation and receipt emails.")
    parser.add_argument("--currency", default="USD")
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Automatically approves the dry-run purchase using the generated token.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    email_gateway = ConsoleEmailGateway()
    workflow = AutonomousPurchaseWorkflow.with_defaults(email_gateway=email_gateway)

    request = PurchaseRequest(
        product_prompt=args.product_prompt,
        price_min=args.min_price,
        price_max=args.max_price,
        confirmation_email=args.email,
        currency=args.currency,
    )

    try:
        pending = workflow.prepare_purchase(request)
        recommendation = pending.recommendation.candidate
        print("Recommended product:")
        print(f"  Name: {recommendation.name}")
        print(f"  Seller: {recommendation.seller}")
        print(f"  Price: {pending.request.currency} {recommendation.price}")
        print(f"  URL: {recommendation.url}")
        print()

        approval_token = pending.approval_token if args.auto_approve else input(
            "Paste the approval token from the confirmation email to proceed: "
        ).strip()
        outcome = workflow.confirm_and_purchase(pending, approval_token)
    except PurchaseAgentError as exc:
        print(f"Purchase workflow failed: {exc}")
        return 1

    print(f"Purchase workflow completed with order ID {outcome.receipt.order_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
