import { Link } from 'react-router-dom';
import Topbar from '../components/Topbar';

export default function ContactPage() {
  return (
    <div className="auth-page">
      <Topbar variant="minimal" />
      <main className="auth-main">
        <div className="auth-card policy-card" role="main">
          <h1 className="auth-card-title">Contact Us</h1>

          <div className="policy-body">
            <h2>Support</h2>
            <p>For questions about your account, practice content, or anything else, email us at:</p>
            <p><a href="mailto:support@datanest.app" className="contact-email">support@datanest.app</a></p>
            <p>We aim to respond within <strong>2 business days</strong>.</p>

            <h2>Billing disputes</h2>
            <p>If you have a question about a charge, please email <a href="mailto:support@datanest.app">support@datanest.app</a> with the subject line "Billing dispute". Include your registered email address and your <strong>Razorpay order or payment ID</strong> so we can look up the transaction quickly.</p>
            <p>See also: <Link to="/refund-policy">Refund Policy</Link>.</p>

            <h2>Privacy requests</h2>
            <p>To request access to, correction of, or deletion of your personal data, email <a href="mailto:support@datanest.app">support@datanest.app</a> with "Data request" in the subject line. We will respond within 14 days.</p>
          </div>

          <div className="policy-footer-nav">
            <Link to="/" className="btn btn-secondary">Back to home</Link>
          </div>
        </div>
      </main>
    </div>
  );
}
