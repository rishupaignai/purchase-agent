# Multi-agent purchase assistant architecture

This project is intentionally structured around small, auditable agents. Each
agent owns one decision boundary, while adapters isolate external systems.

## Flow

```text
User prompt + price range
        |
        v
IntakeAgent
        |
        v
ResearchAgent -> ResearchProvider
        |
        v
RecommendationAgent
        |
        v
ConfirmationAgent -> EmailGateway
        |
        v
Approval token returned by user
        |
        v
PurchaseExecutionAgent -> PurchaseExecutor
        |
        v
PostPurchaseAgent -> EmailGateway
```

## Safety principles

- The user-defined maximum price is enforced before recommendation.
- Purchase execution requires a matching approval token from the confirmation
  step.
- Confirmation emails include product, seller, price, URL, and reasoning so the
  user can audit the choice.
- The default purchase executor is a dry run and cannot spend money.
- External capabilities are adapter-based so real credentials and side effects
  can be reviewed separately from orchestration logic.

## Production checklist

Before connecting real purchasing capabilities:

1. Use a transactional email provider for `EmailGateway`.
2. Use vetted product data sources for `ResearchProvider`; prefer official
   marketplace or merchant APIs over scraping.
3. Implement `PurchaseExecutor` against a checkout API that supports idempotency,
   order preview, cancellation, and receipt retrieval.
4. Store secrets in managed secret storage, never in prompts or source files.
5. Add durable audit logs for request, candidates, recommendation, confirmation,
   approval, purchase request, and receipt.
6. Add policy controls for blocked goods, restricted regions, taxes, shipping,
   return windows, and maximum allowed spend.
7. Require strong user authentication before accepting an approval token.
8. Add human escalation for ambiguous products, low confidence, age-restricted
   goods, medical products, financial products, weapons, and unusually expensive
   purchases.
9. Add monitoring and alerting for checkout failures, duplicate order attempts,
   and provider errors.

## Suggested next integrations

- Replace `MockCatalogResearchProvider` with a product-search provider that
  returns normalized candidates.
- Replace `ConsoleEmailGateway` with an email provider such as SES, SendGrid, or
  Postmark.
- Keep `DryRunPurchaseExecutor` in development and introduce a separate
  production executor with sandbox tests before enabling live checkout.
