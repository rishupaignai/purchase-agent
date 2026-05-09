# purchase-agent

A safe starter kit for a multi-agent purchasing assistant. The workflow accepts
what a user wants to buy plus a price range, researches candidate products,
emails a confirmation request, and only executes the purchase after the user
returns the approval token. The included purchase adapter is a dry run, so the
demo never spends money.

## Agent workflow

1. **Intake Agent** validates the product prompt, price range, email address,
   and currency.
2. **Research Agent** asks a research provider for products and filters them to
   the approved price range.
3. **Recommendation Agent** selects the best candidate and records why it was
   chosen.
4. **Confirmation Agent** sends a pre-purchase email containing the product
   details and approval token.
5. **Purchase Execution Agent** refuses to continue unless the approval token
   matches.
6. **Post-Purchase Agent** sends the order receipt email.

See [docs/architecture.md](docs/architecture.md) for production integration
guidance and safety controls.

## Run the dry-run demo

```bash
python3 -m purchase_agent.cli "noise cancelling headphones" \
  --min-price 100 \
  --max-price 200 \
  --email buyer@example.com
```

The console email gateway prints a confirmation email. Paste the approval token
from that email to simulate the purchase and receive the post-purchase email.

For non-interactive local demos only:

```bash
python3 -m purchase_agent.cli "coffee maker" \
  --max-price 100 \
  --email buyer@example.com \
  --auto-approve
```

## Run tests

```bash
python3 -m unittest discover -s tests
```

## Replacing the dry-run adapters

Production deployments should implement the adapter protocols in
`purchase_agent/adapters.py`:

- `ResearchProvider` for live search, marketplace APIs, or curated vendor APIs.
- `EmailGateway` for transactional email.
- `PurchaseExecutor` for checkout APIs.

Keep the confirmation token gate in place when replacing adapters. Real purchase
execution also needs secrets management, payment authorization, fraud controls,
audit logging, refund handling, legal review, and marketplace terms-of-service
checks.
