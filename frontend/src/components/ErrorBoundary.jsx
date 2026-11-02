// src/components/ErrorBoundary.jsx
import React from 'react';
import { AlertTriangle, RotateCcw } from './Icons';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="page-center">
          <div className="card" style={{ maxWidth: '480px', width: '100%', textAlign: 'center', padding: '36px 28px' }}>
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: 'var(--r-md)',
                background: 'var(--status-danger-bg)',
                color: 'var(--status-danger)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '16px',
              }}
            >
              <AlertTriangle size={22} />
            </div>
            <h2 style={{ marginBottom: '8px', fontSize: '1.25rem' }}>Something went wrong</h2>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '20px' }}>
              {this.state.error?.message || 'An unexpected interface error occurred.'}
            </p>
            <button
              type="button"
              className="btn btn--primary btn--sm"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              <RotateCcw size={15} />
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
