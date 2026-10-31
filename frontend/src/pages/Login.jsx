// src/pages/Login.jsx
import { useState, useEffect } from 'react';
import { supabase } from '../lib/SupabaseClient';

/**
 * Maps raw Supabase / GoTrue / network errors to human-friendly messages.
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
    return 'Unable to send recovery email. Supabase hourly quota reached or custom SMTP is required.';
  }
  if (raw.includes('provider is not enabled') || raw.includes('unsupported provider')) {
    return 'This OAuth provider is not yet enabled in the Supabase Dashboard.';
  }
  if (raw.includes('failed to fetch') || raw.includes('networkerror') || raw.includes('offline')) {
    return 'Unable to connect to the authentication service. Check your internet connection.';
  }

  return err.message || 'Authentication failed. Please try again.';
}

/**
 * Calculates password strength score (0 to 3):
 * 0: Weak (<6 chars)
 * 1: Fair (6+ chars, letters only)
 * 2: Good (6+ chars, numbers + letters)
 * 3: Strong (8+ chars, upper + lower + numbers/symbols)
 */
function getPasswordStrength(pwd) {
  if (!pwd || pwd.length < 6) return { score: 0, label: 'Too short', color: 'hsl(0, 72%, 50%)' };
  let strength = 1;
  if (/\d/.test(pwd) && /[a-zA-Z]/.test(pwd)) strength += 1;
  if (pwd.length >= 8 && /[A-Z]/.test(pwd) && /[^a-zA-Z0-9]/.test(pwd)) strength += 1;

  if (strength === 1) return { score: 1, label: 'Weak', color: 'hsl(38, 92%, 50%)' };
  if (strength === 2) return { score: 2, label: 'Good', color: 'hsl(213, 94%, 68%)' };
  return { score: 3, label: 'Strong', color: 'hsl(142, 71%, 45%)' };
}

export default function Login({
  initialMode = 'signin',
  targetRole = 'learner',
  onBackToLanding,
  onRecoveryComplete,
}) {
  const [mode, setMode] = useState(() => {
    const recoveryUrl =
      (window.location.hash || '').includes('type=recovery') ||
      (window.location.search || '').includes('type=recovery');
    return initialMode === 'recovery' || recoveryUrl ? 'recovery' : initialMode;
  }); // 'signin' | 'signup' | 'recovery'

  const [role, setRole] = useState(targetRole); // 'learner' | 'mentor'
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [username, setUsername] = useState('');
  const [usernameStatus, setUsernameStatus] = useState('idle'); // 'idle' | 'checking' | 'available' | 'taken' | 'invalid'
  const [usernameMsg, setUsernameMsg] = useState('');
  const [status, setStatus] = useState(targetRole === 'mentor' ? 'Industry Mentor' : 'Student');
  const [headline, setHeadline] = useState('');
  const [bio, setBio] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [toast, setToast] = useState(null); // { type: 'success' | 'error' | 'info', text: string }
  const [loading, setLoading] = useState(false);
  const [activeModal, setActiveModal] = useState(null);

  // Sync role if prop updates
  useEffect(() => {
    if (targetRole) {
      setRole(targetRole);
      setStatus(targetRole === 'mentor' ? 'Industry Mentor' : 'Student');
    }
  }, [targetRole]);

  // Debounced real-time username availability check
  useEffect(() => {
    if (!username.trim() || mode !== 'signup') {
      setUsernameStatus('idle');
      setUsernameMsg('');
      return;
    }

    const clean = username.trim().toLowerCase();
    if (clean.length < 3) {
      setUsernameStatus('invalid');
      setUsernameMsg('Username must be at least 3 characters.');
      return;
    }
    if (!/^[a-z0-9_]+$/.test(clean)) {
      setUsernameStatus('invalid');
      setUsernameMsg('Only lowercase letters, numbers, and underscores allowed.');
      return;
    }

    setUsernameStatus('checking');
    setUsernameMsg('Checking availability…');

    const timer = setTimeout(async () => {
      try {
        const { data, error } = await supabase
          .from('profiles')
          .select('id')
          .ilike('username', clean)
          .maybeSingle();

        if (error && error.code !== 'PGRST116') {
          setUsernameStatus('idle');
          return;
        }

        if (data) {
          setUsernameStatus('taken');
          setUsernameMsg('Username already taken ✗');
        } else {
          setUsernameStatus('available');
          setUsernameMsg('Username available ✓');
        }
      } catch {
        setUsernameStatus('idle');
      }
    }, 350);

    return () => clearTimeout(timer);
  }, [username, mode]);

  // Auto-dismiss toast after 5 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // Listen for Supabase password recovery
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY') {
        setMode('recovery');
        setToast({ type: 'info', text: 'Recovery link verified. Please choose a new secure password.' });
      }
    });
    return () => subscription.unsubscribe();
  }, []);

  const handleSocialLogin = async (provider) => {
    setLoading(true);
    setToast(null);
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/`,
          data: {
            role,
            status,
            headline: headline.trim() || (role === 'mentor' ? 'Industry Mentor' : undefined),
            bio: bio.trim() || undefined,
            linkedin_url: linkedinUrl.trim() || undefined,
          },
        },
      });
      if (error) throw error;
    } catch (err) {
      console.error(`Social auth (${provider}) error:`, err);
      setToast({ type: 'error', text: mapAuthError(err) });
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async () => {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes('@') || !cleanEmail.includes('.')) {
      setToast({ type: 'error', text: 'Please enter a valid email address to receive reset instructions.' });
      return;
    }
    setLoading(true);
    setToast(null);
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(cleanEmail, {
        redirectTo: `${window.location.origin}/`,
      });
      if (error) throw error;
      setToast({ type: 'success', text: `Password reset link sent to ${cleanEmail}. Check your inbox.` });
    } catch (err) {
      console.error('Password reset error:', err);
      setToast({ type: 'error', text: mapAuthError(err) });
    } finally {
      setLoading(false);
    }
  };

  const handleCompletePasswordReset = async (e) => {
    e.preventDefault();
    setToast(null);

    if (newPassword.length < 6) {
      setToast({ type: 'error', text: 'Password must be at least 6 characters long.' });
      return;
    }
    if (newPassword !== confirmPassword) {
      setToast({ type: 'error', text: 'Passwords do not match. Please verify both inputs.' });
      return;
    }

    setLoading(true);
    try {
      const { data: sessionData } = await supabase.auth.getSession();
      if (!sessionData?.session) {
        throw new Error('Your reset token is invalid or expired. Please request a new link.');
      }

      const { error } = await supabase.auth.updateUser({ password: newPassword });
      if (error) throw error;

      await supabase.auth.signOut();
      setToast({
        type: 'success',
        text: 'Password updated successfully! Please sign in with your new password.',
      });
      setMode('signin');
      setNewPassword('');
      setConfirmPassword('');
      setPassword('');

      if (window.history.replaceState) {
        window.history.replaceState(null, '', window.location.pathname);
      }
      if (onRecoveryComplete) onRecoveryComplete();
    } catch (err) {
      console.error('Update password error:', err);
      setToast({ type: 'error', text: mapAuthError(err) });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setToast(null);

    const cleanEmail = email.trim().toLowerCase();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!cleanEmail || !emailRegex.test(cleanEmail)) {
      setToast({ type: 'error', text: 'Please enter a valid email address (e.g. user@domain.com).' });
      return;
    }

    setLoading(true);
    try {
      if (mode === 'signup') {
        const cleanFirst = firstName.trim();
        const cleanLast = lastName.trim();
        if (!cleanFirst || !cleanLast) {
          setToast({ type: 'error', text: 'First name and last name are required.' });
          setLoading(false);
          return;
        }

        const fullName = `${cleanFirst} ${cleanLast}`;
        const cleanUser = username.trim().toLowerCase();
        if (cleanUser && (usernameStatus === 'taken' || usernameStatus === 'invalid')) {
          setToast({ type: 'error', text: 'Please choose an available username before submitting.' });
          setLoading(false);
          return;
        }

        const metaData = {
          full_name: fullName,
          first_name: cleanFirst,
          last_name: cleanLast,
          username: cleanUser || undefined,
          role,
          status,
          headline: headline.trim() || (role === 'mentor' ? 'Industry Mentor' : undefined),
          bio: bio.trim() || undefined,
          linkedin_url: linkedinUrl.trim() || undefined,
        };

        const { data, error } = await supabase.auth.signUp({
          email: cleanEmail,
          password,
          options: { data: metaData },
        });
        if (error) throw error;

        if (!data.session) {
          setToast({
            type: 'success',
            text: 'Account created! Please check your email to verify your address, then sign in.',
          });
        }
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email: cleanEmail,
          password,
        });
        if (error) throw error;
      }
    } catch (err) {
      console.error('Auth error:', err);
      setToast({ type: 'error', text: mapAuthError(err) });
    } finally {
      setLoading(false);
    }
  };

  const isSignUp = mode === 'signup';
  const isRecovery = mode === 'recovery';
  const pwdStrength = isSignUp ? getPasswordStrength(password) : isRecovery ? getPasswordStrength(newPassword) : null;

  return (
    <div
      style={{
        minHeight: '100svh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '32px 16px',
        background: 'var(--bg-base)',
        position: 'relative',
      }}
    >
      {/* Toast Notification Banner (Floating top-right) */}
      {toast && (
        <div
          role="status"
          style={{
            position: 'fixed',
            top: '24px',
            right: '24px',
            maxWidth: '380px',
            padding: '14px 18px',
            borderRadius: 'var(--r-md)',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.45)',
            background:
              toast.type === 'error'
                ? 'hsl(0, 60%, 15%)'
                : toast.type === 'success'
                ? 'hsl(142, 60%, 15%)'
                : 'hsl(213, 60%, 15%)',
            border:
              toast.type === 'error'
                ? '1px solid hsl(0, 70%, 40%)'
                : toast.type === 'success'
                ? '1px solid hsl(142, 70%, 40%)'
                : '1px solid hsl(213, 70%, 40%)',
            color: '#fff',
            fontSize: '0.88rem',
            animation: 'fadeIn 0.2s ease',
          }}
        >
          <span>{toast.text}</span>
          <button
            type="button"
            onClick={() => setToast(null)}
            style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', padding: 0 }}
          >
            ✕
          </button>
        </div>
      )}

      <div style={{ maxWidth: '480px', width: '100%' }}>
        {/* Back button */}
        {onBackToLanding && (
          <button
            type="button"
            onClick={onBackToLanding}
            className="btn btn--ghost btn--sm"
            style={{ marginBottom: '20px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            ← Back to Home
          </button>
        )}

        {/* Branding */}
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <div className="logo-mark__icon" style={{ width: '36px', height: '36px', fontSize: '0.95rem' }}>CB</div>
            <span style={{ fontWeight: 800, fontSize: '1.35rem', letterSpacing: '-0.02em' }}>Career Beacon</span>
          </div>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
            AI-powered labor-market intelligence &amp; verified mentorship
          </p>
        </div>

        {/* Auth Card */}
        <div
          className="card"
          style={{
            padding: '32px 28px',
            border: '1px solid var(--border)',
            background: 'var(--bg-surface)',
            borderRadius: 'var(--r-lg)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
          }}
        >
          {/* Card Header */}
          <div style={{ marginBottom: '20px' }}>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: '6px' }}>
              {isRecovery
                ? 'Choose a New Password'
                : isSignUp
                ? `Create ${role === 'mentor' ? 'Mentor' : 'Learner'} Account`
                : 'Welcome Back'}
            </h2>
            <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              {isRecovery
                ? 'Enter and confirm your new secure password.'
                : isSignUp
                ? role === 'mentor'
                  ? 'Connect with learners, answer targeted Q&As, and host 1-on-1 advisory sessions.'
                  : 'Map your skills to industry taxonomies and access noise-filtered micro-learning.'
                : 'Sign in to access your dashboard, skill graph, and scheduled sessions.'}
            </p>
          </div>

          {/* Role selector tab on signup */}
          {isSignUp && !isRecovery && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '6px',
                background: 'var(--bg-elevated)',
                padding: '4px',
                borderRadius: 'var(--r-md)',
                marginBottom: '20px',
                border: '1px solid var(--border)',
              }}
            >
              <button
                type="button"
                className={`btn btn--sm ${role === 'learner' ? 'btn--primary' : 'btn--ghost'}`}
                onClick={() => { setRole('learner'); setStatus('Student'); }}
                style={{ fontSize: '0.85rem', padding: '8px 12px' }}
              >
                🎓 I am a Learner
              </button>
              <button
                type="button"
                className={`btn btn--sm ${role === 'mentor' ? 'btn--primary' : 'btn--ghost'}`}
                onClick={() => { setRole('mentor'); setStatus('Industry Mentor'); }}
                style={{ fontSize: '0.85rem', padding: '8px 12px' }}
              >
                🧑‍🏫 I am a Mentor
              </button>
            </div>
          )}

          {/* RECOVERY MODE FORM */}
          {isRecovery ? (
            <form onSubmit={handleCompletePasswordReset} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '6px' }}>
                  New Password
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    placeholder="At least 6 characters"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    minLength={6}
                    style={{ width: '100%', paddingRight: '40px' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword((p) => !p)}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                    }}
                  >
                    {showNewPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
                {/* Strength meter for new password */}
                {newPassword && (
                  <div style={{ marginTop: '8px' }}>
                    <div style={{ display: 'flex', gap: '4px', height: '4px', marginBottom: '4px' }}>
                      <div
                        style={{
                          flex: 1,
                          borderRadius: '2px',
                          background: pwdStrength?.score >= 1 ? pwdStrength.color : 'var(--border)',
                          transition: 'background 0.2s',
                        }}
                      />
                      <div
                        style={{
                          flex: 1,
                          borderRadius: '2px',
                          background: pwdStrength?.score >= 2 ? pwdStrength.color : 'var(--border)',
                          transition: 'background 0.2s',
                        }}
                      />
                      <div
                        style={{
                          flex: 1,
                          borderRadius: '2px',
                          background: pwdStrength?.score >= 3 ? pwdStrength.color : 'var(--border)',
                          transition: 'background 0.2s',
                        }}
                      />
                    </div>
                    <span style={{ fontSize: '0.72rem', color: pwdStrength?.color, fontWeight: 500 }}>
                      Strength: {pwdStrength?.label}
                    </span>
                  </div>
                )}
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '6px' }}>
                  Confirm New Password
                </label>
                <input
                  type={showNewPassword ? 'text' : 'password'}
                  placeholder="Repeat new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  style={{ width: '100%' }}
                />
                {confirmPassword && (
                  <span
                    style={{
                      fontSize: '0.75rem',
                      display: 'block',
                      marginTop: '4px',
                      color: newPassword === confirmPassword ? 'hsl(142, 75%, 60%)' : 'hsl(0, 80%, 65%)',
                    }}
                  >
                    {newPassword === confirmPassword ? '✓ Passwords match' : '✗ Passwords do not match'}
                  </span>
                )}
              </div>

              <button type="submit" className="btn btn--primary btn--full" disabled={loading} style={{ marginTop: '8px' }}>
                {loading ? 'Updating Password...' : 'Save New Password'}
              </button>
            </form>
          ) : (
            /* STANDARD SIGN-IN & SIGN-UP FORM */
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {isSignUp && (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '6px' }}>
                        First Name
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Alex"
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        required
                        style={{ width: '100%' }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '6px' }}>
                        Last Name
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Kim"
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                        required
                        style={{ width: '100%' }}
                      />
                    </div>
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <label style={{ fontSize: '0.82rem', fontWeight: 600 }}>Unique Username</label>
                      {usernameMsg && (
                        <span
                          style={{
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            color:
                              usernameStatus === 'available'
                                ? 'hsl(142, 75%, 55%)'
                                : usernameStatus === 'taken' || usernameStatus === 'invalid'
                                ? 'hsl(0, 80%, 65%)'
                                : 'var(--text-muted)',
                          }}
                        >
                          {usernameMsg}
                        </span>
                      )}
                    </div>
                    <div style={{ position: 'relative' }}>
                      <span
                        style={{
                          position: 'absolute',
                          left: '12px',
                          top: '50%',
                          transform: 'translateY(-50%)',
                          color: 'var(--text-muted)',
                          fontSize: '0.9rem',
                        }}
                      >
                        @
                      </span>
                      <input
                        type="text"
                        placeholder="alex_kim"
                        value={username}
                        onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                        required
                        minLength={3}
                        maxLength={25}
                        style={{ width: '100%', paddingLeft: '28px' }}
                      />
                    </div>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '6px' }}>
                      {role === 'mentor' ? 'Current Title / Headline' : 'Professional Status'}
                    </label>
                    {role === 'learner' ? (
                      <select
                        value={status}
                        onChange={(e) => setStatus(e.target.value)}
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          borderRadius: 'var(--r-md)',
                          background: 'var(--bg-input)',
                          border: '1px solid var(--border)',
                          color: 'var(--text-primary)',
                          fontSize: '0.9rem',
                        }}
                      >
                        <option value="Student">Student / Recent Graduate</option>
                        <option value="Working Professional">Working Professional / Career Changer</option>
                        <option value="Self-Taught">Self-Taught Developer / Independent</option>
                      </select>
                    ) : (
                      <input
                        type="text"
                        placeholder="e.g. Senior Software Architect at Safaricom"
                        value={headline}
                        onChange={(e) => setHeadline(e.target.value)}
                        required
                        style={{ width: '100%' }}
                      />
                    )}
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '6px' }}>
                      {role === 'mentor' ? 'Mentorship Expertise (Bio)' : 'Primary Learning Goal (Optional)'}
                    </label>
                    <textarea
                      rows={2}
                      placeholder={
                        role === 'mentor'
                          ? 'e.g. 8 years building distributed microservices; mentoring in system design.'
                          : 'e.g. Transitioning from academic software engineering to full-stack dev.'
                      }
                      value={bio}
                      onChange={(e) => setBio(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        borderRadius: 'var(--r-md)',
                        background: 'var(--bg-input)',
                        border: '1px solid var(--border)',
                        color: 'var(--text-primary)',
                        fontSize: '0.88rem',
                        resize: 'none',
                      }}
                    />
                  </div>

                  {role === 'mentor' && (
                    <div>
                      <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '6px' }}>
                        LinkedIn Profile URL (Optional)
                      </label>
                      <input
                        type="url"
                        placeholder="https://linkedin.com/in/username"
                        value={linkedinUrl}
                        onChange={(e) => setLinkedinUrl(e.target.value)}
                        style={{ width: '100%' }}
                      />
                    </div>
                  )}
                </>
              )}

              {/* Email */}
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '6px' }}>
                  Email Address
                </label>
                <input
                  type="email"
                  placeholder="name@organization.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  style={{ width: '100%' }}
                />
              </div>

              {/* Password */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label style={{ fontSize: '0.82rem', fontWeight: 600 }}>Password</label>
                  {!isSignUp && (
                    <button
                      type="button"
                      onClick={handleResetPassword}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: 'var(--accent-light)',
                        fontSize: '0.78rem',
                        cursor: 'pointer',
                        padding: 0,
                      }}
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={6}
                    autoComplete={isSignUp ? 'new-password' : 'current-password'}
                    style={{ width: '100%', paddingRight: '40px' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((p) => !p)}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                    }}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>

                {/* Password strength visual meter */}
                {isSignUp && password && (
                  <div style={{ marginTop: '8px' }}>
                    <div style={{ display: 'flex', gap: '4px', height: '4px', marginBottom: '4px' }}>
                      <div
                        style={{
                          flex: 1,
                          borderRadius: '2px',
                          background: pwdStrength.score >= 1 ? pwdStrength.color : 'var(--border)',
                          transition: 'background 0.2s',
                        }}
                      />
                      <div
                        style={{
                          flex: 1,
                          borderRadius: '2px',
                          background: pwdStrength.score >= 2 ? pwdStrength.color : 'var(--border)',
                          transition: 'background 0.2s',
                        }}
                      />
                      <div
                        style={{
                          flex: 1,
                          borderRadius: '2px',
                          background: pwdStrength.score >= 3 ? pwdStrength.color : 'var(--border)',
                          transition: 'background 0.2s',
                        }}
                      />
                    </div>
                    <span style={{ fontSize: '0.72rem', color: pwdStrength.color, fontWeight: 500 }}>
                      Strength: {pwdStrength.label}
                    </span>
                  </div>
                )}
              </div>

              <button
                type="submit"
                className="btn btn--primary btn--full"
                disabled={loading}
                style={{ marginTop: '8px', padding: '12px', fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
              >
                {loading ? (
                  <>
                    <span className="spinner" style={{ width: '16px', height: '16px' }} />
                    {isSignUp ? 'Creating your account…' : 'Signing you in…'}
                  </>
                ) : isSignUp ? (
                  `Register as ${role === 'mentor' ? 'Mentor' : 'Learner'}`
                ) : (
                  'Sign In'
                )}
              </button>

              {/* Social Login Separator */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  margin: '8px 0',
                  color: 'var(--text-muted)',
                  fontSize: '0.78rem',
                }}
              >
                <div style={{ flex: 1, height: '1px', background: 'var(--border)' }} />
                <span>OR SIGN IN WITH</span>
                <div style={{ flex: 1, height: '1px', background: 'var(--border)' }} />
              </div>

              {/* 3 Active OAuth Providers: Google, GitHub, LinkedIn */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
                {/* Google */}
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  onClick={() => handleSocialLogin('google')}
                  disabled={loading}
                  title="Sign in with Google"
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', fontSize: '0.8rem' }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24">
                    <path
                      fill="#EA4335"
                      d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"
                    />
                    <path
                      fill="#4285F4"
                      d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.8s.2-2.1.4-2.8L1.9 6.3C.7 8.7 0 10.3 0 12s.7 3.3 1.9 5.7l3.7-2.9z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16C3.7 20.4 7.5 23 12 23z"
                    />
                  </svg>
                  Google
                </button>

                {/* GitHub */}
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  onClick={() => handleSocialLogin('github')}
                  disabled={loading}
                  title="Sign in with GitHub"
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', fontSize: '0.8rem' }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2A10 10 0 0 0 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.1-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0 0 12 2Z" />
                  </svg>
                  GitHub
                </button>

                {/* LinkedIn */}
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  onClick={() => handleSocialLogin('linkedin_oidc')}
                  disabled={loading}
                  title="Sign in with LinkedIn"
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', fontSize: '0.8rem' }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="#0A66C2">
                    <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 10.9v8.37H9.2V10.9H6.46M7.83 6.64a1.62 1.62 0 1 0 0 3.24 1.62 1.62 0 0 0 0-3.24Z" />
                  </svg>
                  LinkedIn
                </button>
              </div>

              {/* Mode switch */}
              <p style={{ textAlign: 'center', marginTop: '16px', fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
                {isSignUp ? 'Already have an account?' : "Don't have an account yet?"}{' '}
                <button
                  type="button"
                  onClick={() => {
                    setMode((m) => (m === 'signup' ? 'signin' : 'signup'));
                    setToast(null);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--accent-light)',
                    fontWeight: 600,
                    cursor: 'pointer',
                    padding: 0,
                  }}
                >
                  {isSignUp ? 'Sign in here' : 'Register here'}
                </button>
              </p>
            </form>
          )}
        </div>

        {/* Legal links */}
        <p style={{ textAlign: 'center', marginTop: '20px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          By continuing, you agree to our{' '}
          <button
            type="button"
            onClick={() => setActiveModal('terms')}
            style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', textDecoration: 'underline', cursor: 'pointer', padding: 0 }}
          >
            Terms of Service
          </button>{' '}
          and{' '}
          <button
            type="button"
            onClick={() => setActiveModal('privacy')}
            style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', textDecoration: 'underline', cursor: 'pointer', padding: 0 }}
          >
            Privacy Policy
          </button>
          .
        </p>
      </div>

      {/* Modal */}
      {activeModal && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px',
            zIndex: 100,
          }}
          onClick={() => setActiveModal(null)}
        >
          <div
            className="card"
            style={{ maxWidth: '500px', width: '100%', padding: '24px', background: 'var(--bg-elevated)', borderRadius: 'var(--r-lg)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: '12px' }}>
              {activeModal === 'terms' ? 'Terms of Service' : 'Privacy Policy'}
            </h3>
            <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '20px' }}>
              {activeModal === 'terms'
                ? 'Career Beacon is an educational platform providing AI-driven skill mapping and mentorship sessions. By registering, you agree to uphold academic honesty and respect mentor availability.'
                : 'Your profile data and assessment scores are protected and never distributed. Machine learning embeddings are stored securely via Supabase pgvector.'}
            </p>
            <button
              type="button"
              className="btn btn--secondary btn--sm"
              onClick={() => setActiveModal(null)}
              style={{ float: 'right' }}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
