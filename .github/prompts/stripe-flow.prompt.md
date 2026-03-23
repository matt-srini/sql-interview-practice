---
description: Handles payment workflows, processes events, and triggers plan transitions via plan-change. No entitlement logic.
---

## Objective
Integrate external payment systems (Stripe) to trigger plan transitions via plan-change.

## Inputs
- payment events (checkout, webhooks)
- user reference (user_id)

## Outputs
- validated plan change trigger (calls plan-change)
- event processing result (success/failure)
- audit/log records

## Invariants / Rules
- No direct plan mutation; must use plan-change
- Idempotent, event-driven, deterministic mapping
- All webhooks verified for authenticity
- Handles out-of-order/duplicate events
- Extensible for multiple providers

## Event Mapping
- payment_success → upgrade plan
- subscription_created/updated → assign/modify plan
- payment_failed → no change
- refund_processed → downgrade/revoke plan

## Error Handling / Edge Cases
- Invalid signature: reject
- Unknown event: log/ignore
- Mapping failure: log, avoid partial updates
- plan-change failure: retry/queue
- Dev mode: simulate webhooks

## Extension Points
- Additional payment providers
- Configurable event mapping

## Example Usage
- POST /api/stripe/webhook { event: "payment_success", user_id: X }
