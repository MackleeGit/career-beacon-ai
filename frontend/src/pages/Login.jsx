// src/pages/Login.jsx
import { useState, useEffect } from 'react';
import { supabase } from '../lib/SupabaseClient';

export default function Login() {
  const [mode, setMode]         = useState('signin'); // 'signin' | 'signup'
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [msg, setMsg]           = useState(null);   // { type: 'error'|'success', text }
  const [loading, setLoading]   = useState(false);

  useEffect(() => {
    if (!import.meta.env.VITE_SUPABASE_URL || !import.meta.env.VITE_SUPABASE_ANON_KEY) {
      setMsg({ type: 'error', text: 'Supabase environment variables not set. Check .env file.' });
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMsg(null);
    setLoading(true);
    try {
      if (mode === 'signup') {
        const { data, error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        // Profile row is created automatically by the `on_auth_user_created` DB trigger.
        // If email confirmation is OFF, signUp returns a live session and onAuthStateChange
        // in App.jsx will auto-navigate. The message below is a fallback for when
        // confirmation is ON (user won't be redirected automatically).
        if (!data.session) {
          setMsg({ type: 'success', text: 'Account created — check your email to confirm, then sign in.' });
        }
        // If data.session exists, App.jsx picks it up and navigates automatically.
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        // App.jsx will detect the session and unmount this page automatically.
      }
    } catch (err) {
      console.error('Auth error:', err);
      setMsg({ type: 'error', text: err.message || 'Authentication failed.' });
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setMode((m) => (m === 'signin' ? 'signup' : 'signin'));
    setMsg(null);
  };

  const isSignUp = mode === 'signup';

  return (
    <>
      {/* Background orbs */}
      <div className="bg-orb bg-orb--1" />
      <div className="bg-orb bg-orb--2" />

      <div className="page-center">
        <div className="container">
          {/* Branding */}
          <div style={{ textAlign: 'center', marginBottom: '40px' }}>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '16px' }}>
              <div className="logo-mark">
                <div className="logo-mark__icon">🧭</div>
                Career Beacon
              </div>
            </div>
            <p style={{ fontSize: '0.95rem' }}>
              AI-powered mentorship &amp; micro-learning marketplace
            </p>
          </div>

          {/* Card */}
          <div className="card">
            <h2 style={{ marginBottom: '6px' }}>
              {isSignUp ? 'Create your account' : 'Welcome back'}
            </h2>
            <p style={{ marginBottom: '28px', fontSize: '0.9rem' }}>
              {isSignUp
                ? 'Start your personalised learning journey.'
                : 'Sign in to continue your learning path.'}
            </p>

            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="login-email">Email</label>
                <input
                  id="login-email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>

              <div className="form-group">
                <label htmlFor="login-password">Password</label>
                <input
                  id="login-password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  autoComplete={isSignUp ? 'new-password' : 'current-password'}
                />
              </div>

              <button
                id="auth-submit-btn"
                type="submit"
                className="btn btn--primary btn--full"
                disabled={loading}
                style={{ marginTop: '4px' }}
              >
                {loading ? (
                  <>
                    <span className="spinner" />
                    {isSignUp ? 'Creating account…' : 'Signing in…'}
                  </>
                ) : isSignUp ? 'Create account' : 'Sign in'}
              </button>
            </form>

            {msg && (
              <div className={`alert alert--${msg.type}`}>{msg.text}</div>
            )}

            <div className="divider">or</div>

            <p style={{ textAlign: 'center', fontSize: '0.9rem' }}>
              {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
              <button
                id="auth-toggle-btn"
                type="button"
                onClick={toggleMode}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--accent-light)',
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  fontFamily: 'inherit',
                  padding: 0,
                }}
              >
                {isSignUp ? 'Sign in' : 'Register'}
              </button>
            </p>
          </div>

          <p style={{ textAlign: 'center', marginTop: '20px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            By continuing you agree to our Terms of Service and Privacy Policy.
          </p>
        </div>
      </div>
    </>
  );
}
