// src/pages/Login.jsx
import { useState, useEffect } from 'react';
import { supabase } from '../lib/SupabaseClient';

/**
 * Maps raw Supabase / GoTrue / network errors to human-friendly messages.
 * Prevents technical exposure while providing actionable guidance.
 */
function mapAuthError(err) {
  if (!err) return 'An unexpected error occurred. Please try again.';
  const raw = (typeof err === 'string' ? err : err.message || '').toLowerCase();

  if (raw.includes('invalid login credentials') || raw.includes('invalid_grant')) {
    return 'Incorrect email or password. Please verify your details or reset your password.';
  }
  if (raw.includes('user already registered') || raw.includes('already exists')) {
    return 'An account with this email already exists. Please sign in instead.';
  }
  if (raw.includes('email not confirmed')) {
    return 'Please confirm your email address. Check your inbox for the verification link.';
  }
  if (raw.includes('password') && raw.includes('characters')) {
    return 'Password must be at least 6 characters long.';
  }
  if (raw.includes('rate limit') || raw.includes('too many requests') || raw.includes('over_email_send_rate_limit')) {
    return 'Too many attempts. For your security, please wait a few minutes before trying again.';
  }
  if (raw.includes('error sending recovery email')) {
    return 'Unable to send recovery email. This typically occurs when Supabase hourly email limits are reached, custom SMTP credentials are misconfigured, or localhost:5173 is not in your Redirect URLs.';
  }
  if (raw.includes('provider is not enabled') || raw.includes('unsupported provider') || raw.includes('provider_not_found')) {
    return 'This social login provider is not currently configured in the Supabase project. Please use email & password.';
  }
  if (raw.includes('failed to fetch') || raw.includes('networkerror') || raw.includes('offline')) {
    return 'Unable to reach the authentication service. Please check your internet connection.';
  }
  if (raw.includes('for security purposes, you can only request this once every')) {
    return 'Password reset requested too recently. Please wait 60 seconds before requesting again.';
  }

  return err.message || 'Authentication failed. Please try again.';
}

export default function Login({ initialMode = 'signin', onRecoveryComplete }) {
  const [mode, setMode]                 = useState(() => {
    const recoveryUrl = (window.location.hash || '').includes('type=recovery') || (window.location.search || '').includes('type=recovery');
    return initialMode === 'recovery' || recoveryUrl ? 'recovery' : initialMode;
  }); // 'signin' | 'signup' | 'recovery'
  const [email, setEmail]               = useState('');
  const [password, setPassword]         = useState('');
  const [newPassword, setNewPassword]   = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [msg, setMsg]                   = useState(() => {
    const recoveryUrl = (window.location.hash || '').includes('type=recovery') || (window.location.search || '').includes('type=recovery');
    return initialMode === 'recovery' || recoveryUrl
      ? { type: 'info', text: 'Please enter your new password to complete account recovery.' }
      : null;
  });   // { type: 'error'|'success', text }
  const [loading, setLoading]           = useState(false);
  const [activeModal, setActiveModal]   = useState(null); // null | 'terms' | 'privacy'

  // Detect recovery mode from URL hash or Supabase auth event on mount
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY') {
        setMode('recovery');
        setMsg({ type: 'info', text: 'Recovery link verified. Please choose a new password.' });
      }
    });

    return () => subscription.unsubscribe();
  }, [initialMode]);

  // --- Social login handler with robust try/catch/finally ---
  const handleSocialLogin = async (provider) => {
    setLoading(true);
    setMsg(null);
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/`,
        },
      });
      if (error) throw error;
      // Note: On browser redirect, the window navigates away.
      // If popup or redirect fails, finally ensures loading is reset.
    } catch (err) {
      console.error(`Social auth (${provider}) error:`, err);
      setMsg({ type: 'error', text: mapAuthError(err) });
    } finally {
      setLoading(false);
    }
  };

  // --- Password reset email handler with trimmed email & normalized flow ---
  const handleResetPassword = async () => {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      setMsg({ type: 'error', text: 'Please enter your email to receive a password reset link.' });
      return;
    }
    setLoading(true);
    setMsg(null);
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(cleanEmail, {
        redirectTo: `${window.location.origin}/`,
      });
      if (error) throw error;
      setMsg({ type: 'success', text: `Password reset link sent to ${cleanEmail}. Check your inbox.` });
    } catch (err) {
      console.error('Password reset request error:', err);
      setMsg({ type: 'error', text: mapAuthError(err) });
    } finally {
      setLoading(false);
    }
  };

  // --- Password update completion handler (for recovery flow) ---
  const handleCompletePasswordReset = async (e) => {
    e.preventDefault();
    setMsg(null);

    if (newPassword.length < 6) {
      setMsg({ type: 'error', text: 'New password must be at least 6 characters long.' });
      return;
    }
    if (newPassword !== confirmPassword) {
      setMsg({ type: 'error', text: 'Passwords do not match. Please re-enter.' });
      return;
    }

    setLoading(true);
    try {
      // 1. Cryptographically verify that an active session was established by the recovery token
      const { data: sessionData } = await supabase.auth.getSession();
      if (!sessionData?.session) {
        throw new Error('Your password reset link is invalid or has expired. Please request a new link.');
      }

      // 2. Perform password update
      const { error } = await supabase.auth.updateUser({ password: newPassword });
      if (error) throw error;

      // 3. Clear temporary recovery session for maximum security so user logs in cleanly
      await supabase.auth.signOut();

      setMsg({
        type: 'success',
        text: 'Your password has been updated successfully! Please sign in with your new password.',
      });
      setMode('signin');
      setNewPassword('');
      setConfirmPassword('');
      setPassword('');

      // Clean up URL parameters
      if (window.history.replaceState) {
        window.history.replaceState(null, '', window.location.pathname);
      }

      if (onRecoveryComplete) {
        onRecoveryComplete();
      }
    } catch (err) {
      console.error('Update password error:', err);
      setMsg({ type: 'error', text: mapAuthError(err) });
    } finally {
      setLoading(false);
    }
  };

  // --- Main sign-in / sign-up submit handler ---
  const handleSubmit = async (e) => {
    e.preventDefault();
    setMsg(null);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      setMsg({ type: 'error', text: 'Please enter a valid email address.' });
      return;
    }

    setLoading(true);
    try {
      if (mode === 'signup') {
        const { data, error } = await supabase.auth.signUp({
          email: cleanEmail,
          password,
        });
        if (error) throw error;

        if (!data.session) {
          setMsg({
            type: 'success',
            text: 'Account created! Please check your email to confirm your account, then sign in.',
          });
        }
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email: cleanEmail,
          password,
        });
        if (error) throw error;
        // App.jsx will observe session update and transition state automatically
      }
    } catch (err) {
      console.error('Auth error:', err);
      setMsg({ type: 'error', text: mapAuthError(err) });
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setMode((m) => (m === 'signin' ? 'signup' : 'signin'));
    setMsg(null);
  };

  const isSignUp = mode === 'signup';
  const hasSupabaseConfig = Boolean(import.meta.env.VITE_SUPABASE_URL && import.meta.env.VITE_SUPABASE_ANON_KEY);
  const isRecovery = mode === 'recovery';

  return (
    <>
      {/* Background ambient orbs */}
      <div className="bg-orb bg-orb--1" />
      <div className="bg-orb bg-orb--2" />

      <div className="page-center">
        <div className="container" style={{ maxWidth: '440px', width: '100%' }}>
          {/* Branding */}
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '16px' }}>
              <div className="logo-mark">
                <div className="logo-mark__icon">CB</div>
                Career Beacon
              </div>
            </div>
            <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)' }}>
              AI-powered mentorship &amp; labor-market intelligence
            </p>
          </div>

          {/* Card */}
          <div className="card" style={{ padding: '32px 28px' }}>
            <h2 style={{ marginBottom: '6px', fontSize: '1.45rem' }}>
              {isRecovery
                ? 'Reset your password'
                : isSignUp
                ? 'Create your account'
                : 'Welcome back'}
            </h2>
            <p style={{ marginBottom: '24px', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
              {isRecovery
                ? 'Enter and confirm your new secure password below.'
                : isSignUp
                ? 'Start your personalized labor-market learning journey.'
                : 'Sign in to continue your personalized career path.'}
            </p>

            {/* PASSWORD RECOVERY FORM */}
            {isRecovery ? (
              <form onSubmit={handleCompletePasswordReset}>
                <div className="form-group">
                  <label htmlFor="recovery-new-password">New Password</label>
                  <div style={{ position: 'relative' }}>
                    <input
                      id="recovery-new-password"
                      type={showNewPassword ? 'text' : 'password'}
                      placeholder="At least 6 characters"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      required
                      minLength={6}
                      autoComplete="new-password"
                      style={{ paddingRight: '42px', width: '100%' }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword((prev) => !prev)}
                      aria-label={showNewPassword ? 'Hide password' : 'Show password'}
                      style={eyeButtonStyle}
                    >
                      {showNewPassword ? <EyeOffIcon /> : <EyeIcon />}
                    </button>
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="recovery-confirm-password">Confirm New Password</label>
                  <input
                    id="recovery-confirm-password"
                    type={showNewPassword ? 'text' : 'password'}
                    placeholder="Repeat new password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    minLength={6}
                    autoComplete="new-password"
                    style={{ width: '100%' }}
                  />
                </div>

                <button
                  id="auth-recovery-submit-btn"
                  type="submit"
                  className="btn btn--primary btn--full"
                  disabled={loading}
                  style={{ marginTop: '8px' }}
                >
                  {loading ? (
                    <>
                      <span className="spinner" /> Updating password…
                    </>
                  ) : (
                    'Update password & continue'
                  )}
                </button>

                <p style={{ textAlign: 'center', marginTop: '16px', fontSize: '0.88rem' }}>
                  <button
                    type="button"
                    onClick={() => {
                      setMode('signin');
                      setMsg(null);
                    }}
                    style={textLinkStyle}
                  >
                    ← Back to sign in
                  </button>
                </p>
              </form>
            ) : (
              /* STANDARD SIGN IN / SIGN UP FORM */
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
                    style={{ width: '100%' }}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="login-password">Password</label>
                  <div style={{ position: 'relative' }}>
                    <input
                      id="login-password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={6}
                      autoComplete={isSignUp ? 'new-password' : 'current-password'}
                      style={{ paddingRight: '42px', width: '100%' }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((prev) => !prev)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      style={eyeButtonStyle}
                    >
                      {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                    </button>
                  </div>
                </div>

                {!isSignUp && (
                  <p style={{ textAlign: 'right', marginTop: '2px', marginBottom: '4px' }}>
                    <button
                      id="forgot-password-btn"
                      type="button"
                      onClick={handleResetPassword}
                      disabled={loading}
                      style={{
                        ...textLinkStyle,
                        fontSize: '0.82rem',
                      }}
                    >
                      Forgot password?
                    </button>
                  </p>
                )}

                <button
                  id="auth-submit-btn"
                  type="submit"
                  className="btn btn--primary btn--full"
                  disabled={loading}
                  style={{ marginTop: '8px' }}
                >
                  {loading ? (
                    <>
                      <span className="spinner" />
                      {isSignUp ? 'Creating account…' : 'Signing in…'}
                    </>
                  ) : isSignUp ? (
                    'Create account'
                  ) : (
                    'Sign in'
                  )}
                </button>
              </form>
            )}

            {/* Alert Message Box */}
            {!hasSupabaseConfig && !msg && (
              <div className="alert alert--error" style={{ marginTop: '16px', fontSize: '0.86rem' }}>
                Supabase environment variables not set. Check .env file.
              </div>
            )}
            {msg && (
              <div
                className={`alert alert--${msg.type === 'info' ? 'success' : msg.type}`}
                style={{ marginTop: '16px', fontSize: '0.86rem', lineHeight: '1.4' }}
              >
                {msg.text}
              </div>
            )}

            {/* Social Logins (Only when not in password recovery mode) */}
            {!isRecovery && (
              <>
                <div className="divider">or continue with</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '12px' }}>
                  <button
                    type="button"
                    onClick={() => handleSocialLogin('google')}
                    className="btn btn--secondary btn--full"
                    disabled={loading}
                    style={{
                      backgroundColor: 'hsla(0, 0%, 100%, 0.05)',
                      color: 'var(--text-primary)',
                      border: '1px solid var(--border)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '10px',
                    }}
                  >
                    <GoogleIcon />
                    Continue with Google
                  </button>

                  <button
                    type="button"
                    onClick={() => handleSocialLogin('linkedin_oidc')}
                    className="btn btn--secondary btn--full"
                    disabled={loading}
                    style={{
                      backgroundColor: 'hsla(210, 80%, 45%, 0.12)',
                      color: 'hsl(210, 95%, 75%)',
                      border: '1px solid hsla(210, 80%, 45%, 0.35)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '10px',
                    }}
                  >
                    <LinkedInIcon />
                    Continue with LinkedIn
                  </button>
                </div>

                <p style={{ textAlign: 'center', marginTop: '20px', fontSize: '0.9rem' }}>
                  {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
                  <button
                    id="auth-toggle-btn"
                    type="button"
                    onClick={toggleMode}
                    style={{
                      ...textLinkStyle,
                      fontWeight: 600,
                    }}
                  >
                    {isSignUp ? 'Sign in' : 'Register'}
                  </button>
                </p>
              </>
            )}
          </div>

          {/* Terms & Privacy Links with Accessible Dialogs */}
          <p style={{ textAlign: 'center', marginTop: '20px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            By continuing, you agree to our{' '}
            <button
              type="button"
              onClick={() => setActiveModal('terms')}
              style={policyLinkStyle}
            >
              Terms of Service
            </button>{' '}
            and{' '}
            <button
              type="button"
              onClick={() => setActiveModal('privacy')}
              style={policyLinkStyle}
            >
              Privacy Policy
            </button>
            .
          </p>
        </div>
      </div>

      {/* Accessible Policy Modal */}
      {activeModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="policy-modal-title"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '16px',
          }}
          onClick={() => setActiveModal(null)}
        >
          <div
            className="card"
            style={{
              maxWidth: '520px',
              width: '100%',
              maxHeight: '80vh',
              overflowY: 'auto',
              position: 'relative',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 id="policy-modal-title">
                {activeModal === 'terms' ? 'Terms of Service' : 'Privacy Policy'}
              </h3>
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                aria-label="Close dialog"
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  fontSize: '1.25rem',
                  cursor: 'pointer',
                  padding: '4px 8px',
                }}
              >
                ✕
              </button>
            </div>

            {activeModal === 'terms' ? (
              <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                <p style={{ marginBottom: '12px' }}>
                  <strong>1. Educational Guidance:</strong> Career Beacon provides labor-market alignment insights, personalized diagnostic roadmaps, and micro-learning modules based on public taxonomies (ESCO/O*NET) and AI synthesis.
                </p>
                <p style={{ marginBottom: '12px' }}>
                  <strong>2. User Accounts:</strong> You are responsible for safeguarding your credentials and any actions performed under your account.
                </p>
                <p>
                  <strong>3. Acceptable Use:</strong> You agree not to abuse, reverse engineer, or scrape learning content or backend career graph APIs.
                </p>
              </div>
            ) : (
              <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                <p style={{ marginBottom: '12px' }}>
                  <strong>1. Information Collection:</strong> We collect your email address, profile name, and career goals to build your personalized skill trees and track lesson progress.
                </p>
                <p style={{ marginBottom: '12px' }}>
                  <strong>2. Data Protection:</strong> Authentication and user security are powered by Supabase with Row Level Security (RLS) and encrypted password hashing. We never sell your personal data.
                </p>
                <p>
                  <strong>3. Third-Party OAuth:</strong> If you sign in via Google or LinkedIn, we only access your verified email and basic profile information as granted by your OAuth provider.
                </p>
              </div>
            )}

            <div style={{ marginTop: '24px', textAlign: 'right' }}>
              <button
                type="button"
                className="btn btn--primary btn--sm"
                onClick={() => setActiveModal(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// --- Inline SVG Icons & Styles ---

function EyeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24">
      <path
        fill="#EA4335"
        d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 8.9 5 12 5z"
      />
      <path
        fill="#4285F4"
        d="M23.5 12.3c0-.8-.1-1.7-.2-2.3H12v4.6h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.9z"
      />
      <path
        fill="#FBBC05"
        d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 12 0 14.5s.7 4.8 1.9 7.2l3.7-2.9z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3.1 0-5.5-2.1-6.4-5.2L1.9 17c1.8 3.7 5.6 7 10.1 7z"
      />
    </svg>
  );
}

function LinkedInIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 8.76a1.46 1.46 0 1 0 0-2.92 1.46 1.46 0 0 0 0 2.92m1.37 9.74v-8.37H5.09v8.37h2.74z" />
    </svg>
  );
}

const eyeButtonStyle = {
  position: 'absolute',
  right: '10px',
  top: '50%',
  transform: 'translateY(-50%)',
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  color: 'var(--text-secondary)',
  padding: '4px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

const textLinkStyle = {
  background: 'none',
  border: 'none',
  color: 'var(--accent-light)',
  cursor: 'pointer',
  fontSize: '0.9rem',
  fontFamily: 'inherit',
  padding: 0,
};

const policyLinkStyle = {
  background: 'none',
  border: 'none',
  color: 'var(--accent-light)',
  cursor: 'pointer',
  fontSize: '0.78rem',
  fontFamily: 'inherit',
  textDecoration: 'underline',
  padding: 0,
};
