import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Topbar from '../components/Topbar';

export default function PrivacyPolicyPage({ isModal = false }) {
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
      <h1 className="auth-card-title">Privacy Policy</h1>
      <p className="policy-meta">Last updated: April 2025</p>

      <div className="policy-body">
        <h2>What we collect</h2>
        <p>When you create an account we collect your email address and, optionally, your display name. If you sign in with Google or GitHub we receive the email and name from that provider. We do not store passwords for OAuth sign-ins.</p>
        <p>When you make a payment, Razorpay collects your card or bank details directly. We receive only a Razorpay customer ID and payment event notifications — we never see or store raw card numbers.</p>
        <p>We collect product usage data (questions solved, session durations, feature interactions) to improve the platform. This data is tied to your account.</p>

        <h2>How we use it</h2>
        <ul>
          <li><strong>Authentication</strong> — to sign you in and keep your session.</li>
          <li><strong>Billing</strong> — to manage your subscription or one-time purchase via Razorpay.</li>
          <li><strong>Product improvement</strong> — to understand which features are working and where users get stuck.</li>
          <li><strong>Transactional email</strong> — to send password reset and email verification messages.</li>
        </ul>
        <p>We do not sell your data to third parties, and we do not use your data for advertising.</p>

        <h2>Cookies and local storage</h2>
        <p>We set a <strong>session cookie</strong> (HttpOnly, SameSite=Strict) to authenticate your requests. We use <strong>localStorage</strong> for your theme preference (light/dark) and first-visit walkthrough state. No advertising or cross-site tracking cookies are used.</p>

        <h2>Third-party processors</h2>
        <ul>
          <li><strong>Razorpay</strong> — payment processing (India). Their privacy policy applies to payment data.</li>
          <li><strong>Resend</strong> — transactional email delivery.</li>
          <li><strong>Sentry</strong> — error tracking. Errors may include anonymised stack traces and browser metadata.</li>
          <li><strong>PostHog</strong> — product analytics. Session data is anonymised and stored on PostHog's EU infrastructure.</li>
        </ul>

        <h2>Data retention</h2>
        <p>Your account and progress data are retained for as long as your account is active. If you delete your account, your personal data is removed within 30 days.</p>

        <h2>Your rights</h2>
        <p>You may request access to, correction of, or deletion of your personal data at any time by emailing <a href="mailto:support@datathink.co">support@datathink.co</a>. We will respond within 14 days.</p>

        <h2>Contact</h2>
        <p>Questions about this policy: <a href="mailto:support@datathink.co">support@datathink.co</a></p>
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
