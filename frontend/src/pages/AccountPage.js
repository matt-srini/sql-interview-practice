import { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import Topbar from '../components/Topbar';

const PLAN_LABELS = {
  free: 'Free',
  pro: 'Pro',
  elite: 'Elite',
  lifetime_pro: 'Lifetime Pro',
  lifetime_elite: 'Lifetime Elite',
};

const LIFETIME_PLANS = new Set(['lifetime_pro', 'lifetime_elite']);
const SUBSCRIPTION_PLANS = new Set(['pro', 'elite']);

function formatDate(unixSeconds) {
  if (!unixSeconds) return null;
  return new Date(unixSeconds * 1000).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

export default function AccountPage() {
  const { user, loading: authLoading } = useAuth();

  const plan = user?.plan ?? 'free';
  const normalisedPlan = plan.startsWith('lifetime_') ? plan.replace('lifetime_', '') : plan;
  const isPaying = normalisedPlan === 'pro' || normalisedPlan === 'elite';
  const planLabel = PLAN_LABELS[plan] ?? plan;
  const planPillNode = isPaying
    ? <span className={`shell-pill shell-pill-plan shell-pill-plan-${normalisedPlan}`}>{planLabel}</span>
    : null;

  const isSubscription = SUBSCRIPTION_PLANS.has(plan);
  const isLifetime = LIFETIME_PLANS.has(plan);

  const [showConfirm, setShowConfirm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [cancelAt, setCancelAt] = useState(null); // Unix timestamp
  const [error, setError] = useState(null);
  const cancelled = cancelAt !== null;

  async function handleConfirmCancel() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.post('/account/cancel-subscription');
      setCancelAt(res.data.cancel_at);
      setShowConfirm(false);
    } catch (err) {
      const msg = err?.response?.data?.error ?? 'Something went wrong. Please try again.';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Helmet>
        <title>Account — datathink</title>
      </Helmet>
      <Topbar userExtras={planPillNode} />

      <main className="container" style={{ maxWidth: 640, padding: '3rem 1.5rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-strong)', margin: '0 0 2rem' }}>
          Account
        </h1>

        {/* Plan card */}
        <section
          style={{
            background: 'var(--surface-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            padding: '1.5rem',
            marginBottom: '1.5rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
            <span style={{ fontWeight: 600, color: 'var(--text-strong)', fontSize: '1rem' }}>
              Current plan
            </span>
            {isPaying ? (
              <span className={`shell-pill shell-pill-plan shell-pill-plan-${normalisedPlan}`}>
                {planLabel}
              </span>
            ) : (
              <span className="shell-pill">{planLabel}</span>
            )}
          </div>

          {isLifetime && (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: '0.5rem 0 0' }}>
              Lifetime access — no renewal required.
            </p>
          )}

          {isSubscription && !cancelled && (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: '0.5rem 0 0' }}>
              Monthly subscription — renews automatically each billing cycle.
            </p>
          )}

          {!isPaying && !authLoading && (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: '0.5rem 0 0' }}>
              <Link to="/#landing-pricing" style={{ color: 'var(--accent)' }}>
                Upgrade to Pro or Elite
              </Link>{' '}
              to unlock all questions and mock interviews.
            </p>
          )}

          {/* Success state */}
          {cancelled && (
            <div
              style={{
                marginTop: '1rem',
                padding: '0.875rem 1rem',
                background: 'color-mix(in srgb, var(--success) 12%, transparent)',
                border: '1px solid color-mix(in srgb, var(--success) 35%, transparent)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--success)',
                fontSize: '0.875rem',
                fontWeight: 500,
              }}
            >
              Subscription cancelled —{' '}
              {cancelAt
                ? <>your access continues until <strong>{formatDate(cancelAt)}</strong>.</>
                : 'your access continues until the end of the current billing period.'}
            </div>
          )}

          {/* Error state */}
          {error && (
            <div
              style={{
                marginTop: '1rem',
                padding: '0.875rem 1rem',
                background: 'color-mix(in srgb, var(--danger) 12%, transparent)',
                border: '1px solid color-mix(in srgb, var(--danger) 35%, transparent)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--danger)',
                fontSize: '0.875rem',
              }}
            >
              {error}
            </div>
          )}

          {/* Cancel button — only for active monthly subscriptions */}
          {isSubscription && !cancelled && (
            <div style={{ marginTop: '1.25rem' }}>
              <button
                type="button"
                className="btn btn-danger"
                onClick={() => { setError(null); setShowConfirm(true); }}
              >
                Cancel subscription
              </button>
            </div>
          )}
        </section>
      </main>

      {/* Confirmation modal */}
      {showConfirm && (
        <div
          className="mock-modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="cancel-modal-title"
          onClick={() => !submitting && setShowConfirm(false)}
        >
          <div className="mock-modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="mock-modal-title" id="cancel-modal-title">
              Cancel subscription?
            </h2>
            <p className="mock-modal-body">
              Your access continues until the end of the current billing period. After that,
              your account moves to Free and locked questions will no longer be accessible.
            </p>
            <div className="mock-modal-actions">
              <button
                type="button"
                className="btn btn-secondary"
                disabled={submitting}
                onClick={() => setShowConfirm(false)}
              >
                Keep subscription
              </button>
              <button
                type="button"
                className="btn btn-danger"
                disabled={submitting}
                onClick={handleConfirmCancel}
              >
                {submitting ? 'Cancelling…' : 'Confirm cancellation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
