import { Component } from 'react';
import { Link } from 'react-router-dom';
import * as Sentry from '@sentry/react';

/**
 * React Error Boundary — catches unhandled JS exceptions in the component tree
 * and renders a recovery UI instead of a blank/crashed page.
 *
 * Must be a class component: React error boundaries require componentDidCatch.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary] Uncaught error:', error, info?.componentStack);
    Sentry.captureException(error, { contexts: { react: { componentStack: info?.componentStack } } });
  }

  handleReset() {
    this.setState({ hasError: false, error: null });
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div className="error-boundary-page">
        <div className="error-boundary-card">
          <div className="error-boundary-icon" aria-hidden="true">⚠</div>
          <h1 className="error-boundary-title">Something went wrong</h1>
          <p className="error-boundary-body">
            An unexpected error occurred. Try reloading — if the problem persists,{' '}
            <a href="mailto:support@datathink.co">contact us</a> and we'll fix it promptly.
          </p>
          <div className="error-boundary-actions">
            <button
              className="btn btn-primary"
              onClick={() => {
                this.handleReset();
                window.location.href = '/';
              }}
            >
              Go to home
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => window.location.reload()}
            >
              Reload page
            </button>
          </div>
          {import.meta.env.DEV && this.state.error && (
            <details className="error-boundary-details">
              <summary>Error details (dev only)</summary>
              <pre>{this.state.error?.toString()}</pre>
            </details>
          )}
        </div>
      </div>
    );
  }
}
