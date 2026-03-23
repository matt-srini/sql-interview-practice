# Stripe Integration Layer

## Objective
Define how external payment systems (e.g., Stripe) integrate with the platform to enable plan upgrades and downgrades. This layer is responsible for handling payment workflows, processing asynchronous events, and triggering plan transitions via the plan-change layer. It must remain decoupled from entitlement logic and act as a bridge between external billing systems and internal plan state.

## Scope
- Included:
  - Payment session creation (e.g., checkout session initiation)
  - Payment confirmation handling (success/failure)
  - Webhook processing for asynchronous events
  - Mapping payment events to plan transitions
  - Handling refunds, cancellations, and subscription updates
  - Idempotent and resilient event processing
  - Extensible integration points for future payment providers
- Excluded:
  - Plan change API and validation logic (see plan-change.md)
  - Unlock rule logic and entitlement computation (see unlock-system.md)
  - User profile storage and schema (see user-profile.md)
  - UI/UX for payment flows

## Dependencies
- plan-change.md (for triggering validated plan transitions)

## Inputs / Outputs

Inputs:
- payment events:
  - checkout session creation requests
  - webhook events (payment success, failure, refund, subscription updates)
- user reference (user_id or mapped identifier)

Outputs:
- validated plan change trigger (via plan-change layer)
- event processing result (success/failure, idempotent handling)
- audit/log records for payment events

## Key Design Principles
- Decoupled payment and entitlement logic
- No business logic for unlocks or entitlement computation in this layer
- No direct plan mutation; all changes must go through plan-change layer
- Deterministic mapping: same payment event always results in the same plan transition
- Event-driven architecture: all payment confirmations handled via asynchronous webhooks
- Idempotent processing: duplicate or retried webhook events must not cause duplicate plan changes
- Safe handling of out-of-order events (e.g., refund arriving before confirmation)
- All webhook events must be verified for authenticity (e.g., signature validation)
- Resilient to external system failures (retries, partial failures)
- Failed downstream operations (e.g., plan-change failure) must be retried using a reliable retry mechanism
- Extensible to support multiple payment providers without changing core logic
- No awareness of entitlement logic; this layer only translates external events into plan transition intents

## Event Flow Model

Define the high-level flow:

1. User initiates upgrade via frontend
2. Backend creates payment session (Stripe checkout)
3. User completes payment on Stripe
4. Stripe sends webhook event to backend
5. Stripe layer validates and processes event
6. Stripe layer maps event to plan transition
7. Stripe layer calls plan-change layer to update plan
8. plan-change updates user-profile and triggers entitlement recomputation

Notes:
- The system must rely on webhooks (not frontend redirects) as the source of truth for payment success
- Frontend callbacks are informational only and must not trigger plan changes directly

## Event Mapping Rules

Define mapping examples:
- payment_success → upgrade plan (e.g., free → pro)
- subscription_created → assign plan
- subscription_updated → modify plan
- payment_failed → no change
- refund_processed → downgrade or revoke plan (based on policy)

These mappings must be deterministic and configurable.
- External payment events must be translated into internal plan transition intents before invoking plan-change

## Idempotency Strategy

- Each external event must have a unique identifier (e.g., Stripe event_id)
- Maintain processed event registry (or equivalent mechanism)
- If an event is received multiple times:
  - process only once
  - subsequent attempts are no-ops

## Error Handling

- Invalid signature → reject request (security failure)
- Unknown event type → log and ignore safely
- Mapping failure → log error and avoid partial state updates
- plan-change failure → retry or queue for retry

## Implementation Steps

- Implement endpoint: POST /api/stripe/webhook
- Verify webhook signature for authenticity
- Parse event payload and identify event type
- Check idempotency (skip if already processed)
- Map event to plan transition
- Call plan-change layer with required input
- Handle success/failure and log results
- Optionally store processed event IDs for idempotency

## Dev Mode Support

- Allow bypassing Stripe for testing (direct plan-change calls)
- Simulate webhook events for local testing
- Ensure dev-mode behavior mirrors production flow structure

## Security Considerations

- Validate all webhook signatures
- Never trust frontend callbacks for payment success
- Protect endpoints against replay attacks
- Ensure sensitive data is not logged