import { useEffect, useRef, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import Topbar from '../components/Topbar';

// ── Constants ────────────────────────────────────────────────────────────────

const PLAN_LABELS = {
  free: 'Free',
  pro: 'Pro',
  elite: 'Elite',
  lifetime_pro: 'Lifetime Pro',
  lifetime_elite: 'Lifetime Elite',
};

const LIFETIME_PLANS = new Set(['lifetime_pro', 'lifetime_elite']);
const SUBSCRIPTION_PLANS = new Set(['pro', 'elite']);

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(unixSeconds) {
  if (!unixSeconds) return null;
  return new Date(unixSeconds * 1000).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function formatAmount(amountInSmallestUnit, currency) {
  if (!amountInSmallestUnit) return null;
  const amount = amountInSmallestUnit / 100;
  if (currency === 'INR') {
    return `₹${amount.toLocaleString('en-IN')}`;
  }
  return `$${amount.toFixed(2)}`;
}

function normalisePlan(plan) {
  return plan?.startsWith('lifetime_') ? plan.replace('lifetime_', '') : (plan ?? 'free');
}

// ── Status badge component ────────────────────────────────────────────────────

function StatusBadge({ status }) {
  const config = {
    paid:    { bg: 'var(--success-soft)', color: 'var(--success)',  dot: 'var(--success)',  label: 'Paid'    },
    failed:  { bg: 'var(--danger-soft)',  color: 'var(--danger)',   dot: 'var(--danger)',   label: 'Failed'  },
    pending: { bg: 'var(--warning-soft)', color: 'var(--warning)',  dot: 'var(--warning)',  label: 'Pending' },
    unknown: { bg: 'rgba(0,0,0,0.05)',    color: 'var(--text-muted)',dot: 'var(--text-muted)',label: status ?? '—' },
  }[status] ?? { bg: 'rgba(0,0,0,0.05)', color: 'var(--text-muted)', dot: 'var(--text-muted)', label: status ?? '—' };

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.35rem',
        fontSize: '0.78rem',
        fontWeight: 600,
        padding: '0.2rem 0.55rem',
        borderRadius: 999,
        background: config.bg,
        color: config.color,
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: config.dot, flexShrink: 0 }} />
      {config.label}
    </span>
  );
}

// ── Inline alert strip ────────────────────────────────────────────────────────

function Alert({ tone, children }) {
  const styles = {
    success: { bg: 'var(--success-soft)', border: 'color-mix(in srgb, var(--success) 30%, transparent)', color: 'var(--success-text)' },
    warning: { bg: 'var(--warning-soft)', border: 'color-mix(in srgb, var(--warning) 35%, transparent)', color: 'var(--warning-text)' },
    danger:  { bg: 'var(--danger-soft)',  border: 'color-mix(in srgb, var(--danger)  35%, transparent)', color: 'var(--danger-text)'  },
    info:    { bg: 'var(--accent-soft)',  border: 'color-mix(in srgb, var(--accent)  25%, transparent)', color: 'var(--accent)'       },
  }[tone] ?? { bg: 'rgba(0,0,0,0.04)', border: 'var(--border-subtle)', color: 'var(--text-secondary)' };

  return (
    <div
      style={{
        padding: '0.875rem 1rem',
        background: styles.bg,
        border: `1px solid ${styles.border}`,
        borderRadius: 'var(--radius-sm)',
        color: styles.color,
        fontSize: '0.875rem',
        lineHeight: 1.5,
      }}
    >
      {children}
    </div>
  );
}

// ── Section card wrapper ──────────────────────────────────────────────────────

function Card({ children, style }) {
  return (
    <section
      style={{
        background: 'var(--surface-card)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: '1.5rem',
        ...style,
      }}
    >
      {children}
    </section>
  );
}

// ── Switch plan modal ─────────────────────────────────────────────────────────

function SwitchPlanModal({ currentPlan, billing, onClose, onSuccess }) {
  const isProUser = currentPlan === 'pro';
  const targetPlan = isProUser ? 'elite' : 'pro';
  const isUpgrade = isProUser; // pro→elite is upgrade; elite→pro is downgrade

  const [timing, setTiming] = useState(isUpgrade ? 'cycle_end' : 'cycle_end');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const currency = billing?.plan_currency ?? 'INR';
  const targetAmount = billing?.plan_amounts?.[targetPlan];
  const formattedAmount = targetAmount ? formatAmount(targetAmount, currency) : null;
  const cycleEnd = formatDate(billing?.billing_cycle_end);

  async function handleConfirm() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.post('/account/switch-plan', { target_plan: targetPlan, timing });
      onSuccess({ targetPlan, timing, effectiveAt: res.data.effective_at });
    } catch (err) {
      setError(err?.response?.data?.error ?? 'Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  const confirmLabel = isUpgrade
    ? (timing === 'now' ? `Switch to ${PLAN_LABELS[targetPlan]} now` : `Schedule switch to ${PLAN_LABELS[targetPlan]}`)
    : `Confirm downgrade to ${PLAN_LABELS[targetPlan]}`;

  return (
    <div
      className="mock-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="switch-modal-title"
      onClick={() => !submitting && onClose()}
    >
      <div className="mock-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 460 }}>
        <h2 className="mock-modal-title" id="switch-modal-title">
          Switch to {PLAN_LABELS[targetPlan]}
        </h2>

        {isUpgrade ? (
          <div style={{ marginBottom: '1.25rem' }}>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: '0 0 1rem' }}>
              When should the switch happen?
            </p>
            <label
              style={{
                display: 'flex',
                gap: '0.75rem',
                padding: '0.875rem 1rem',
                border: `2px solid ${timing === 'now' ? 'var(--accent)' : 'var(--border-subtle)'}`,
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                marginBottom: '0.625rem',
                background: timing === 'now' ? 'var(--accent-soft)' : 'transparent',
              }}
            >
              <input
                type="radio"
                name="timing"
                value="now"
                checked={timing === 'now'}
                onChange={() => setTiming('now')}
                style={{ marginTop: 2, flexShrink: 0 }}
              />
              <span>
                <strong style={{ color: 'var(--text-strong)', display: 'block', marginBottom: '0.2rem' }}>
                  Switch now{formattedAmount ? ` — charged ${formattedAmount} immediately` : ''}
                </strong>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  No credit for unused {PLAN_LABELS[currentPlan]} days. Your billing cycle resets today.
                </span>
              </span>
            </label>

            <label
              style={{
                display: 'flex',
                gap: '0.75rem',
                padding: '0.875rem 1rem',
                border: `2px solid ${timing === 'cycle_end' ? 'var(--accent)' : 'var(--border-subtle)'}`,
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                background: timing === 'cycle_end' ? 'var(--accent-soft)' : 'transparent',
              }}
            >
              <input
                type="radio"
                name="timing"
                value="cycle_end"
                checked={timing === 'cycle_end'}
                onChange={() => setTiming('cycle_end')}
                style={{ marginTop: 2, flexShrink: 0 }}
              />
              <span>
                <strong style={{ color: 'var(--text-strong)', display: 'block', marginBottom: '0.2rem' }}>
                  Switch at renewal{cycleEnd ? ` — ${PLAN_LABELS[targetPlan]} starts on ${cycleEnd}` : ''}
                </strong>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  {formattedAmount ? `You'll be charged ${formattedAmount} then — no partial charges.` : 'No partial charges.'}
                </span>
              </span>
            </label>
          </div>
        ) : (
          <p className="mock-modal-body">
            You'll stay on {PLAN_LABELS[currentPlan]} until{cycleEnd ? ` ${cycleEnd}` : ' the end of the current billing period'},
            then move to {PLAN_LABELS[targetPlan]}{formattedAmount ? ` at ${formattedAmount}/month` : ''}.
            {' '}Questions exclusive to {PLAN_LABELS[currentPlan]} will no longer be accessible after that date.
          </p>
        )}

        {error && (
          <div style={{ marginBottom: '1rem' }}>
            <Alert tone="danger">{error}</Alert>
          </div>
        )}

        <div className="mock-modal-actions">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={submitting}
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={submitting}
            onClick={handleConfirm}
          >
            {submitting ? 'Confirming…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Reactivate modal ──────────────────────────────────────────────────────────

function ReactivateModal({ plan, billing, onClose, onSuccess }) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const currency = billing?.plan_currency ?? 'INR';
  const currentAmount = billing?.plan_amounts?.[plan];
  const formattedAmount = currentAmount ? formatAmount(currentAmount, currency) : null;
  const cycleEnd = formatDate(billing?.billing_cycle_end);

  async function handleConfirm() {
    setSubmitting(true);
    setError(null);
    try {
      await api.post('/account/reactivate-subscription');
      onSuccess();
    } catch (err) {
      setError(err?.response?.data?.error ?? 'Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="mock-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reactivate-modal-title"
      onClick={() => !submitting && onClose()}
    >
      <div className="mock-modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="mock-modal-title" id="reactivate-modal-title">
          Resume subscription?
        </h2>
        <p className="mock-modal-body">
          You'll continue on {PLAN_LABELS[plan]}{formattedAmount ? ` at ${formattedAmount}/month` : ''}.
          {cycleEnd ? ` Your next billing date will be ${cycleEnd}.` : ''}
        </p>

        {error && (
          <div style={{ marginBottom: '1rem' }}>
            <Alert tone="danger">{error}</Alert>
          </div>
        )}

        <div className="mock-modal-actions">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={submitting}
            onClick={onClose}
          >
            Keep cancelled
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={submitting}
            onClick={handleConfirm}
          >
            {submitting ? 'Resuming…' : 'Resume subscription'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Cancel modal ──────────────────────────────────────────────────────────────

function CancelModal({ billing, onClose, onSuccess }) {
  const cycleEnd = formatDate(billing?.billing_cycle_end);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleConfirm() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.post('/account/cancel-subscription');
      onSuccess({ cancelAt: res.data.cancel_at });
    } catch (err) {
      setError(err?.response?.data?.error ?? 'Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="mock-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cancel-modal-title"
      onClick={() => !submitting && onClose()}
    >
      <div className="mock-modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="mock-modal-title" id="cancel-modal-title">
          Cancel subscription?
        </h2>
        <p className="mock-modal-body">
          {cycleEnd
            ? <>Your access continues until <strong>{cycleEnd}</strong>. After that, your account moves to Free and locked questions will no longer be accessible.</>
            : 'Your access continues until the end of the current billing period. After that, your account moves to Free.'}
        </p>

        {error && (
          <div style={{ marginBottom: '1rem' }}>
            <Alert tone="danger">{error}</Alert>
          </div>
        )}

        <div className="mock-modal-actions">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={submitting}
            onClick={onClose}
          >
            Keep subscription
          </button>
          <button
            type="button"
            className="btn btn-danger"
            disabled={submitting}
            onClick={handleConfirm}
          >
            {submitting ? 'Cancelling…' : 'Confirm cancellation'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Delete account modal ─────────────────────────────────────────────────────

const PAID_PLANS = new Set(['pro', 'elite', 'lifetime_pro', 'lifetime_elite']);

function DeleteAccountModal({ userPlan, onClose }) {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [confirmText, setConfirmText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const hasPaidPlan = PAID_PLANS.has(userPlan);
  const confirmed = confirmText.trim().toUpperCase() === 'DELETE';

  async function handleConfirm() {
    setSubmitting(true);
    setError(null);
    try {
      await api.delete('/account/delete');
      await logout();
      navigate('/');
    } catch (err) {
      setError(err?.response?.data?.error ?? 'Something went wrong. Please try again.');
      setSubmitting(false);
    }
  }

  return (
    <div
      className="mock-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-account-modal-title"
      onClick={() => !submitting && onClose()}
    >
      <div className="mock-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 460 }}>
        <h2 className="mock-modal-title" id="delete-account-modal-title">
          Delete account?
        </h2>

        <div className="mock-modal-body" style={{ marginBottom: '1.25rem' }}>
          <p style={{ margin: '0 0 0.75rem' }}>
            This will permanently delete:
          </p>
          <ul style={{ margin: '0 0 0.75rem', paddingLeft: '1.25rem', color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: 1.6 }}>
            <li>Your account and profile</li>
            <li>All progress and solved question history across all tracks</li>
            <li>All submissions and mock interview sessions</li>
          </ul>
          {hasPaidPlan && (
            <p style={{ margin: '0 0 0.75rem', color: 'var(--danger)', fontSize: '0.875rem', fontWeight: 500 }}>
              Your active subscription will be cancelled immediately with no refund.
            </p>
          )}
          <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
            Payment receipts in our billing provider and error-tracking records are retained for financial compliance. All other personal data stored by datathink is permanently removed.
          </p>
        </div>

        <div style={{ marginBottom: '1.25rem' }}>
          <label
            htmlFor="delete-confirm-input"
            style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-strong)', marginBottom: '0.5rem' }}
          >
            Type <strong>DELETE</strong> to confirm
          </label>
          <input
            id="delete-confirm-input"
            type="text"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder="DELETE"
            autoComplete="off"
            disabled={submitting}
            style={{
              width: '100%',
              boxSizing: 'border-box',
              padding: '0.625rem 0.75rem',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.9rem',
              fontFamily: 'var(--font-mono)',
              background: 'var(--bg-page)',
              color: 'var(--text-strong)',
            }}
          />
        </div>

        {error && (
          <div style={{ marginBottom: '1rem' }}>
            <Alert tone="danger">{error}</Alert>
          </div>
        )}

        <div className="mock-modal-actions">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={submitting}
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-danger"
            disabled={!confirmed || submitting}
            onClick={handleConfirm}
          >
            {submitting ? 'Deleting…' : 'Delete my account'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AccountPage() {
  const { user, refreshUser } = useAuth();

  const authPlan = user?.plan ?? 'free';
  const normPlan = normalisePlan(authPlan);
  const isPaying = normPlan === 'pro' || normPlan === 'elite';

  const planPillNode = isPaying
    ? <span className={`shell-pill shell-pill-plan shell-pill-plan-${normPlan}`}>{PLAN_LABELS[authPlan] ?? authPlan}</span>
    : null;

  // ── Profile state ────────────────────────────────────────────────────────
  const [nameEditing, setNameEditing] = useState(false);
  const [nameValue, setNameValue] = useState('');
  const [nameSaving, setNameSaving] = useState(false);
  const [nameError, setNameError] = useState(null);
  const [idCopied, setIdCopied] = useState(false);
  const nameInputRef = useRef(null);

  function handleNameEdit() {
    setNameValue(user?.name || '');
    setNameError(null);
    setNameEditing(true);
    setTimeout(() => nameInputRef.current?.focus(), 0);
  }

  function handleNameCancel() {
    setNameEditing(false);
    setNameError(null);
  }

  async function handleNameSave() {
    const trimmed = nameValue.trim();
    if (!trimmed) { setNameError('Name cannot be empty.'); return; }
    setNameSaving(true);
    setNameError(null);
    try {
      await api.patch('/account/profile', { name: trimmed });
      await refreshUser();
      setNameEditing(false);
    } catch (err) {
      setNameError(err.response?.data?.error || 'Could not save name.');
    } finally {
      setNameSaving(false);
    }
  }

  function handleCopyId() {
    if (!user?.id) return;
    navigator.clipboard.writeText(user.id).then(() => {
      setIdCopied(true);
      setTimeout(() => setIdCopied(false), 2000);
    }).catch(() => {});
  }

  // ── Billing state ────────────────────────────────────────────────────────
  const [billing, setBilling] = useState(null);
  const [billingLoading, setBillingLoading] = useState(true);
  const [billingError, setBillingError] = useState(null);

  // ── Operation state ──────────────────────────────────────────────────────
  const [modal, setModal] = useState(null); // 'cancel' | 'switch' | 'reactivate' | 'delete'
  const [successState, setSuccessState] = useState(null); // { type, ... }

  // ── Load billing on mount ────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setBillingLoading(true);
    api.get('/account/billing')
      .then((res) => { if (!cancelled) setBilling(res.data); })
      .catch(() => { if (!cancelled) setBillingError('Could not load billing information.'); })
      .finally(() => { if (!cancelled) setBillingLoading(false); });
    return () => { cancelled = true; };
  }, []);

  function refetchBilling() {
    setBillingError(null);
    api.get('/account/billing')
      .then((res) => setBilling(res.data))
      .catch(() => {});
  }

  // ── Derived values from billing response ─────────────────────────────────
  const effectivePlan = billing?.plan ?? authPlan;
  const isSubscription = billing?.is_subscription ?? SUBSCRIPTION_PLANS.has(effectivePlan);
  const isLifetime = billing?.is_lifetime ?? LIFETIME_PLANS.has(effectivePlan);
  const cancelledAtCycleEnd = billing?.cancelled_at_cycle_end ?? false;
  const billingCycleEnd = formatDate(billing?.billing_cycle_end);
  const chargeAt = formatDate(billing?.charge_at);
  const normEffective = normalisePlan(effectivePlan);
  const canSwitch = isSubscription && !cancelledAtCycleEnd && !successState;
  const canCancel = isSubscription && !cancelledAtCycleEnd && !successState;

  // ── Helpers for success ───────────────────────────────────────────────
  function handleCancelSuccess({ cancelAt }) {
    setModal(null);
    setSuccessState({ type: 'cancelled', cancelAt });
    setBilling((prev) => prev ? { ...prev, cancelled_at_cycle_end: true, charge_at: null } : prev);
  }

  function handleReactivateSuccess() {
    setModal(null);
    setSuccessState({ type: 'reactivated' });
    refetchBilling();
  }

  function handleSwitchSuccess({ targetPlan, timing, effectiveAt }) {
    setModal(null);
    setSuccessState({ type: 'switched', targetPlan, timing, effectiveAt });
    setTimeout(refetchBilling, 1500);
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <>
      <Helmet>
        <title>Account — datathink</title>
      </Helmet>
      <Topbar userExtras={planPillNode} />

      <main className="container" style={{ maxWidth: 680, padding: '3rem 1.5rem 4rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-strong)', margin: '0 0 1.5rem' }}>
          Account
        </h1>

        {/* ── Profile card ─────────────────────────────────────────── */}
        <Card style={{ marginBottom: '1.25rem' }}>
          <div style={{ fontWeight: 600, color: 'var(--text-strong)', fontSize: '1rem', marginBottom: '0.875rem' }}>
            Profile
          </div>

          {/* Name row */}
          <div className="acct-field-row">
            <span className="acct-field-label">Name</span>
            {nameEditing ? (
              <div className="acct-name-edit">
                <input
                  ref={nameInputRef}
                  className="acct-name-input"
                  value={nameValue}
                  onChange={e => setNameValue(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter') handleNameSave();
                    if (e.key === 'Escape') handleNameCancel();
                  }}
                  maxLength={120}
                  disabled={nameSaving}
                  placeholder="Your name"
                />
                <button className="acct-save-btn" onClick={handleNameSave} disabled={nameSaving}>
                  {nameSaving ? 'Saving…' : 'Save'}
                </button>
                <button className="acct-cancel-btn" onClick={handleNameCancel} disabled={nameSaving}>
                  Cancel
                </button>
                {nameError && <span className="acct-name-error">{nameError}</span>}
              </div>
            ) : (
              <div className="acct-name-display">
                <span style={{ color: user?.name ? 'var(--text-strong)' : 'var(--text-muted)', fontStyle: user?.name ? 'normal' : 'italic' }}>
                  {user?.name || 'Not set'}
                </span>
                <button className="acct-edit-btn" onClick={handleNameEdit} title="Edit name" aria-label="Edit name">
                  ✎
                </button>
              </div>
            )}
          </div>

          {/* Email row */}
          <div className="acct-field-row">
            <span className="acct-field-label">Email</span>
            <span className="acct-field-value">{user?.email}</span>
          </div>

          {/* Account ID row */}
          <div className="acct-field-row">
            <span className="acct-field-label">Account ID</span>
            <button
              className="acct-id-chip"
              onClick={handleCopyId}
              title={idCopied ? 'Copied!' : 'Click to copy full ID'}
              aria-label="Copy account ID"
            >
              <span className="acct-id-chip-text">{user?.id?.slice(0, 8)}…</span>
              <span className="acct-id-chip-icon">{idCopied ? '✓' : '⧉'}</span>
            </button>
          </div>
        </Card>

        {/* ── Billing section ───────────────────────────────────────────── */}
        {billingLoading ? (
          <Card>
            <div style={{ height: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              Loading billing info…
            </div>
          </Card>
        ) : billingError ? (
          <Card>
            <Alert tone="danger">{billingError}</Alert>
          </Card>
        ) : (
          <>
            {/* ── Plan card ─────────────────────────────────────────────── */}
            <Card style={{ marginBottom: '1.25rem' }}>
              {/* Header row */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                <span style={{ fontWeight: 600, color: 'var(--text-strong)', fontSize: '1rem' }}>
                  Current plan
                </span>
                {isPaying || (billing?.is_lifetime) ? (
                  <span className={`shell-pill shell-pill-plan shell-pill-plan-${normEffective}`}>
                    {PLAN_LABELS[effectivePlan] ?? effectivePlan}
                  </span>
                ) : (
                  <span className="shell-pill">{PLAN_LABELS[effectivePlan] ?? 'Free'}</span>
                )}
              </div>

              {/* Billing cycle / expiry */}
              {isSubscription && billing?.billing_cycle_end && !cancelledAtCycleEnd && !successState && (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: '0 0 0.5rem' }}>
                  {chargeAt
                    ? <>Next billing date: <strong style={{ color: 'var(--text-primary)' }}>{chargeAt}</strong></>
                    : <>Billing period ends: <strong style={{ color: 'var(--text-primary)' }}>{billingCycleEnd}</strong></>}
                </p>
              )}

              {isLifetime && (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: '0 0 0.5rem' }}>
                  Lifetime access — no renewal required.
                </p>
              )}

              {!isPaying && !isLifetime && (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: '0 0 0.5rem' }}>
                  <button
                    type="button"
                    onClick={() => navigate('/', { state: { scrollTo: 'landing-pricing' } })}
                    style={{ color: 'var(--accent)', background: 'none', border: 'none', padding: 0, cursor: 'pointer', font: 'inherit', textDecoration: 'underline' }}
                  >
                    Upgrade to Pro or Elite
                  </button>{' '}
                  to unlock all questions and mock interviews.
                </p>
              )}

              {/* Amber cancellation banner */}
              {cancelledAtCycleEnd && !successState && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '1rem',
                    flexWrap: 'wrap',
                    padding: '0.875rem 1rem',
                    marginTop: '0.75rem',
                    background: 'var(--warning-soft)',
                    border: '1px solid color-mix(in srgb, var(--warning) 35%, transparent)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--warning-text)',
                    fontSize: '0.875rem',
                  }}
                >
                  <span>
                    Cancels on <strong>{billingCycleEnd ?? 'end of billing period'}</strong> — access continues until then.
                  </span>
                  <button
                    type="button"
                    className="btn btn-secondary btn-compact"
                    onClick={() => setModal('reactivate')}
                  >
                    Reactivate
                  </button>
                </div>
              )}

              {/* Success states */}
              {successState?.type === 'cancelled' && (
                <div style={{ marginTop: '0.75rem' }}>
                  <Alert tone="success">
                    Subscription cancelled — access continues until{' '}
                    <strong>{successState.cancelAt ? formatDate(successState.cancelAt) : (billingCycleEnd ?? 'end of billing period')}</strong>.
                  </Alert>
                </div>
              )}

              {successState?.type === 'reactivated' && (
                <div style={{ marginTop: '0.75rem' }}>
                  <Alert tone="success">
                    Subscription reactivated — your {PLAN_LABELS[effectivePlan]} plan will continue as normal.
                  </Alert>
                </div>
              )}

              {successState?.type === 'switched' && (
                <div style={{ marginTop: '0.75rem' }}>
                  <Alert tone="success">
                    {successState.timing === 'now'
                      ? <>Switched to {PLAN_LABELS[successState.targetPlan]} — your plan is now active.</>
                      : <>Switch to {PLAN_LABELS[successState.targetPlan]} scheduled
                          {successState.effectiveAt ? <> for <strong>{formatDate(successState.effectiveAt)}</strong></> : ' for your next billing date'}.
                        </>}
                  </Alert>
                </div>
              )}

              {/* Action buttons */}
              {isSubscription && !successState && (
                <div className="account-page-actions" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginTop: '1.25rem' }}>
                  {canSwitch && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => setModal('switch')}
                    >
                      Switch plan
                    </button>
                  )}
                  {canCancel && (
                    <button
                      type="button"
                      className="btn btn-danger"
                      onClick={() => setModal('cancel')}
                    >
                      Cancel subscription
                    </button>
                  )}
                </div>
              )}

              {/* Payment method info note — shown for active monthly subscribers */}
              {isSubscription && !cancelledAtCycleEnd && !successState && (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: '1rem 0 0', lineHeight: 1.5 }}>
                  If a payment fails, Razorpay will email you automatically with a secure link to update your card and retry.
                </p>
              )}
            </Card>

            {/* ── Invoice section ───────────────────────────────────────── */}
            {isSubscription && (
              <Card>
                <h2 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-strong)', margin: '0 0 1rem' }}>
                  Payment history
                </h2>

                {billing?.invoices?.length > 0 ? (
                  <div style={{ overflow: 'auto', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                    <table className="results-table" style={{ fontSize: '0.83rem' }}>
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Amount</th>
                          <th>Status</th>
                          <th>Receipt</th>
                        </tr>
                      </thead>
                      <tbody>
                        {billing.invoices.map((inv) => (
                          <tr key={inv.id}>
                            <td style={{ fontFamily: 'var(--font-sans)', color: 'var(--text-secondary)' }}>
                              {formatDate(inv.date) ?? '—'}
                            </td>
                            <td style={{ fontFamily: 'var(--font-sans)', fontWeight: 500 }}>
                              {inv.amount
                                ? formatAmount(inv.amount, inv.currency)
                                : '—'}
                            </td>
                            <td style={{ fontFamily: 'var(--font-sans)' }}>
                              <StatusBadge status={inv.status} />
                            </td>
                            <td style={{ fontFamily: 'var(--font-sans)' }}>
                              {inv.pdf_url ? (
                                <a
                                  href={inv.pdf_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{ color: 'var(--accent)', textDecoration: 'none', fontSize: '0.8rem' }}
                                >
                                  Download ↗
                                </a>
                              ) : (
                                <span style={{ color: 'var(--text-muted)' }}>—</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: 0 }}>
                    No payment history available yet.
                  </p>
                )}
              </Card>
            )}
          </>
        )}

        {/* ── Danger Zone ───────────────────────────────────────────────── */}
        {user?.email && (
          <>
            <hr style={{ border: 'none', borderTop: '1px solid var(--border-subtle)', margin: '2.5rem 0' }} />
            <section>
              <h2 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--danger)', margin: '0 0 0.5rem' }}>
                Danger zone
              </h2>
              {LIFETIME_PLANS.has(authPlan) ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: 0, lineHeight: 1.6 }}>
                  Lifetime plan accounts are handled manually. To request account deletion, email{' '}
                  <a href="mailto:support@datathink.co" style={{ color: 'var(--accent)' }}>support@datathink.co</a>
                  {' '}— requests are processed within 7 business days.
                </p>
              ) : (
                <>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: '0 0 1rem', lineHeight: 1.5 }}>
                    Permanently deletes your account, all progress, and all data across every track. This cannot be undone.
                  </p>
                  <button
                    type="button"
                    className="btn btn-danger"
                    onClick={() => setModal('delete')}
                  >
                    Delete account
                  </button>
                </>
              )}
            </section>
          </>
        )}
      </main>

      {/* ── Modals ─────────────────────────────────────────────────────────── */}

      {modal === 'cancel' && (
        <CancelModal
          billing={billing}
          onClose={() => setModal(null)}
          onSuccess={handleCancelSuccess}
        />
      )}

      {modal === 'switch' && (
        <SwitchPlanModal
          currentPlan={effectivePlan}
          billing={billing}
          onClose={() => setModal(null)}
          onSuccess={handleSwitchSuccess}
        />
      )}

      {modal === 'reactivate' && (
        <ReactivateModal
          plan={effectivePlan}
          billing={billing}
          onClose={() => setModal(null)}
          onSuccess={handleReactivateSuccess}
        />
      )}

      {modal === 'delete' && (
        <DeleteAccountModal
          userPlan={authPlan}
          onClose={() => setModal(null)}
        />
      )}
    </>
  );
}
