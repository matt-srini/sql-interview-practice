import { Link } from 'react-router-dom';
import Topbar from '../components/Topbar';

export default function TermsPage() {
  return (
    <div className="auth-page">
      <Topbar variant="minimal" />
      <main className="auth-main">
        <div className="auth-card policy-card" role="main">
          <h1 className="auth-card-title">Terms &amp; Conditions</h1>
          <p className="policy-meta">Last updated: April 2025</p>

          <div className="policy-body">
            <h2>Acceptance</h2>
            <p>By accessing or using datathink ("the Service") you agree to these Terms. If you do not agree, do not use the Service.</p>

            <h2>Eligibility</h2>
            <p>You must be at least 18 years old and capable of entering a binding contract. By using the Service you represent that you meet this requirement.</p>

            <h2>Description of the Service</h2>
            <p>datathink is an interactive data interview practice platform offering SQL, Python, Pandas, and PySpark question banks, mock interview sessions, and learning paths. Content is provided for personal, non-commercial skill development.</p>

            <h2>Accounts</h2>
            <p>You are responsible for maintaining the confidentiality of your account credentials. You must notify us immediately at <a href="mailto:support@datathink.co">support@datathink.co</a> if you suspect unauthorised access. We reserve the right to terminate accounts that violate these Terms.</p>

            <h2>Subscriptions and payments</h2>
            <ul>
              <li><strong>Monthly plans (Pro, Elite)</strong> — billed on a recurring monthly basis from the date of purchase. Your subscription renews automatically each month until you cancel.</li>
              <li><strong>Cancellation</strong> — you may cancel at any time from your account settings. Access continues until the end of the current billing period; no partial refunds are issued.</li>
              <li><strong>Lifetime plans</strong> — a one-time purchase granting perpetual access to the plan tier. No recurring charges apply.</li>
              <li><strong>Price changes</strong> — we may change subscription prices with 30 days' notice. You may cancel before the new price takes effect.</li>
            </ul>

            <h2>Refunds</h2>
            <p>Please see our <Link to="/refund-policy">Refund Policy</Link>.</p>

            <h2>Acceptable use</h2>
            <p>You agree not to:</p>
            <ul>
              <li>Share your account credentials or allow others to access your account.</li>
              <li>Scrape, copy, or redistribute question content or datasets from the platform.</li>
              <li>Attempt to reverse-engineer, decompile, or extract the platform's underlying code or data.</li>
              <li>Use automated tools to submit answers or artificially inflate your progress.</li>
              <li>Use the Service for any unlawful purpose.</li>
            </ul>

            <h2>Intellectual property</h2>
            <p>All content on the platform — including question text, datasets, explanations, and code examples — is owned by datathink or its licensors. You are granted a limited, non-transferable licence to use it for personal practice only.</p>

            <h2>Disclaimer of warranties</h2>
            <p>The Service is provided "as is" without warranties of any kind. We do not guarantee that the platform will be error-free, uninterrupted, or that practice questions will guarantee success in any interview.</p>

            <h2>Limitation of liability</h2>
            <p>To the fullest extent permitted by law, datathink's liability for any claim arising from use of the Service is limited to the amount you paid in the 3 months preceding the claim.</p>

            <h2>Governing law</h2>
            <p>These Terms are governed by the laws of India. Any disputes shall be subject to the exclusive jurisdiction of courts in India.</p>

            <h2>Changes to these Terms</h2>
            <p>We may update these Terms from time to time. Continued use after changes are posted constitutes acceptance of the revised Terms.</p>

            <h2>Contact</h2>
            <p><a href="mailto:support@datathink.co">support@datathink.co</a></p>
          </div>

          <div className="policy-footer-nav">
            <Link to="/" className="btn btn-secondary">Back to home</Link>
          </div>
        </div>
      </main>
    </div>
  );
}
