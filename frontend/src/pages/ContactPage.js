import { useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import Topbar from '../components/Topbar';

export default function ContactPage({ isModal = false }) {
  const location = useLocation();
  const navigate = useNavigate();
  const handleClose = () => {
    // Closing the Contact modal returns to the background page (the landing
    // footer) and keeps the scroll position — it does not jump to the top.
    const bg = location.state?.backgroundLocation;
    navigate(bg ? `${bg.pathname}${bg.search}` : '/', { replace: true, state: { preserveScroll: true } });
  };
  const modalLinkState = isModal && location.state?.backgroundLocation
    ? { backgroundLocation: location.state.backgroundLocation }
    : undefined;

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
      <h1 className="auth-card-title">Contact Us</h1>

      <div className="policy-body">
        <h2>Support</h2>
        <p>For questions about your account, practice content, or anything else, email us at:</p>
        <p><a href="mailto:support@datathink.co" className="contact-email">support@datathink.co</a></p>
        <p>We aim to respond within <strong>2 business days</strong>.</p>

        <h2>Billing disputes</h2>
        <p>If you have a question about a charge, please email <a href="mailto:support@datathink.co">support@datathink.co</a> with the subject line "Billing dispute". Include your registered email address and your <strong>Razorpay payment ID</strong> (India/INR purchases) or <strong>Paddle transaction/order ID</strong> (international purchases) so we can look up the transaction quickly.</p>
        <p>See also: <Link to="/refund-policy" state={modalLinkState} replace={isModal}>Refund Policy</Link>.</p>

        <h2>Privacy requests</h2>
        <p>To request access to, correction of, or deletion of your personal data, email <a href="mailto:support@datathink.co">support@datathink.co</a> with "Data request" in the subject line. We will respond within 14 days.</p>
      </div>

      <div className="policy-footer-nav">
        {footerAction}
      </div>
    </div>
  );

  if (isModal) return content;

  return (
    <div className="auth-page">
      <Helmet>
        <title>Contact — datathink</title>
        <meta name="description" content="Get in touch with the datathink team for support or questions about the platform." />
        <meta property="og:title" content="Contact — datathink" />
        <meta property="og:description" content="Get in touch with the datathink team for support or questions about the platform." />
        <meta property="og:url" content="https://datathink.co/contact" />
        <link rel="canonical" href="https://datathink.co/contact" />
      </Helmet>
      <Topbar variant="minimal" />
      <main className="auth-main">
        {content}
      </main>
    </div>
  );
}
