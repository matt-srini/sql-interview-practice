import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Topbar from '../components/Topbar';

export default function RefundPolicyPage({ isModal = false }) {
  const navigate = useNavigate();
  const handleClose = () => navigate(-1);

  useEffect(() => {
    if (!isModal) window.scrollTo(0, 0);
  }, [isModal]);

  const footerAction = isModal ? (
    <button type="button" className="btn btn-secondary" onClick={handleClose}>Close</button>
  ) : (
    <Link to="/" className="btn btn-secondary">Back to home</Link>
  );

  const content = (
    <div className="auth-card policy-card" role="main">
      {isModal && (
        <button type="button" className="policy-exit" onClick={handleClose} aria-label="Close policy">X</button>
      )}
      <h1 className="auth-card-title">Refund Policy</h1>
      <p className="policy-meta">Last updated: April 2025</p>

      <div className="policy-body">
        <h2>Monthly subscriptions</h2>
        <p>Monthly subscription charges (Pro, Elite) are <strong>non-refundable</strong> once the billing cycle has started. You may cancel at any time and you will retain access through the end of the paid period — no further charges will be made after cancellation.</p>

        <h2>Lifetime plans</h2>
        <p>Lifetime plan purchases are <strong>final and non-refundable</strong>. Because lifetime access is granted immediately upon payment, we are unable to issue refunds after the transaction is complete.</p>

        <h2>Exceptions</h2>
        <p>We will review refund requests in the following circumstances:</p>
        <ul>
          <li><strong>Billing errors</strong> — if you were charged an incorrect amount or charged more than once for the same plan.</li>
          <li><strong>Duplicate purchase</strong> — if you accidentally purchased the same plan twice within a short window.</li>
        </ul>
        <p>To be considered, exception requests must be submitted within <strong>7 days</strong> of the transaction date.</p>

        <h2>How to request a review</h2>
        <p>Email <a href="mailto:support@datathink.co">support@datathink.co</a> with the subject line "Billing dispute" and include:</p>
        <ul>
          <li>Your registered email address</li>
          <li>Your Razorpay order or payment ID</li>
          <li>A brief description of the issue</li>
        </ul>
        <p>We will respond within 5 business days.</p>

        <h2>Contact</h2>
        <p><a href="mailto:support@datathink.co">support@datathink.co</a></p>
      </div>

      <div className="policy-footer-nav">
        {footerAction}
      </div>
    </div>
  );

  if (isModal) return content;

  return (
    <div className="auth-page">
      <Topbar variant="minimal" />
      <main className="auth-main">
        {content}
      </main>
    </div>
  );
}
