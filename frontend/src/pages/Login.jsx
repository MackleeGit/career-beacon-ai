// src/pages/Login.jsx
import { useState, useEffect } from 'react';
import { supabase } from '../lib/SupabaseClient';
import ThemeSelector from '../components/ThemeSelector';
import {
  Compass,
  ArrowLeft,
  GraduationCap,
  Users,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  X,
} from '../components/Icons';

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
 */
function getPasswordStrength(pwd) {
  if (!pwd || pwd.length < 6) return { score: 0, label: 'Too short', color: 'var(--status-danger)' };
  let strength = 1;
  if (/\d/.test(pwd) && /[a-zA-Z]/.test(pwd)) strength += 1;
  if (pwd.length >= 8 && /[A-Z]/.test(pwd) && /[^a-zA-Z0-9]/.test(pwd)) strength += 1;

  if (strength === 1) return { score: 1, label: 'Weak', color: 'var(--status-warning)' };
  if (strength === 2) return { score: 2, label: 'Good', color: 'var(--status-info)' };
  return { score: 3, label: 'Strong', color: 'var(--status-success)' };
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
    setUsernameMsg('Checking availability...');

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
          setUsernameMsg('Username already taken');
        } else {
          setUsernameStatus('available');
          setUsernameMsg('Username available');
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
        text: 'Password updated successfully. Please sign in with your new password.',
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

    const inputIdentifier = email.trim();
    if (!inputIdentifier) {
      setToast({ type: 'error', text: mode === 'signup' ? 'Email is required.' : 'Please enter your email or username.' });
      return;
    }

    const rawLower = inputIdentifier.toLowerCase();
    const isLikelyEmail = rawLower.includes('@') && rawLower.includes('.') && !rawLower.startsWith('@');
    let cleanEmail = rawLower;

    // In signin mode, allow logging in with either username (e.g. 'cristiano' or '@cristiano') or email
    if (mode === 'signin') {
      if (!isLikelyEmail) {
        const cleanUser = rawLower.replace(/^@+/, '').trim();
        if (!cleanUser) {
          setToast({ type: 'error', text: 'Please enter a valid username or email address.' });
          return;
        }
        setLoading(true);
        try {
          const { data: prof, error: profErr } = await supabase
            .from('profiles')
            .select('email')
            .ilike('username', cleanUser)
            .limit(1)
            .maybeSingle();

          if (profErr || !prof?.email) {
            setToast({ type: 'error', text: `No account found with username '@${cleanUser}'.` });
            setLoading(false);
            return;
          }
          cleanEmail = prof.email.toLowerCase();
        } catch (lookupErr) {
          setToast({ type: 'error', text: 'Failed to resolve username.' });
          setLoading(false);
          return;
        }
      }
    } else {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!cleanEmail || !emailRegex.test(cleanEmail)) {
        setToast({ type: 'error', text: 'Please enter a valid email address (e.g. user@domain.com).' });
        return;
      }
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
          status: role === 'mentor' ? 'Industry Mentor' : status,
        };

        const { data, error } = await supabase.auth.signUp({
          email: cleanEmail,
          password,
          options: { data: metaData },
        });
        if (error) throw error;

        if (data?.user?.id && cleanUser) {
          try {
            await supabase.from('profiles').update({ username: cleanUser }).eq('id', data.user.id);
          } catch (pErr) {
            console.error('Failed to update profile username:', pErr);
          }
        }

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
        background: 'var(--background)',
        position: 'relative',
      }}
    >
      {/* Top Bar */}
      <header
        style={{
          maxWidth: '1120px',
          width: '100%',
          margin: '0 auto',
          padding: '16px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        {onBackToLanding ? (
          <button
            type="button"
            onClick={onBackToLanding}
            className="btn btn--ghost btn--sm"
          >
            <ArrowLeft size={15} />
            <span>Back to Home</span>
          </button>
        ) : (
          <div className="logo-mark">
            <div className="logo-mark__icon">
              <Compass size={18} />
            </div>
            <span>Career Beacon</span>
          </div>
        )}
        <ThemeSelector />
      </header>

      {/* Toast Notification Banner */}
      {toast && (
        <div
          role="status"
          style={{
            position: 'fixed',
            top: '20px',
            right: '20px',
            maxWidth: '400px',
            padding: '12px 16px',
            borderRadius: 'var(--r-md)',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: '12px',
            boxShadow: 'var(--shadow-lg)',
            background:
              toast.type === 'error'
                ? 'var(--status-danger-bg)'
                : toast.type === 'success'
                ? 'var(--status-success-bg)'
                : 'var(--status-info-bg)',
            border: `1px solid ${
              toast.type === 'error'
                ? 'var(--status-danger-bd)'
                : toast.type === 'success'
                ? 'var(--status-success-bd)'
                : 'var(--status-info-bd)'
            }`,
            color:
              toast.type === 'error'
                ? 'var(--status-danger)'
                : toast.type === 'success'
                ? 'var(--status-success)'
                : 'var(--status-info)',
            fontSize: '0.86rem',
            fontWeight: 500,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
            {toast.type === 'success' ? (
              <CheckCircle2 size={16} style={{ marginTop: '2px' }} />
            ) : (
              <AlertCircle size={16} style={{ marginTop: '2px' }} />
            )}
            <span>{toast.text}</span>
          </div>
          <button
            type="button"
            aria-label="Dismiss notification"
            onClick={() => setToast(null)}
            style={{
              background: 'none',
              border: 'none',
              color: 'currentColor',
              cursor: 'pointer',
              padding: '2px',
              display: 'inline-flex',
            }}
          >
            <X size={15} />
          </button>
        </div>
      )}

      {/* Main Centered Form */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px 16px 48px',
        }}
      >
        <div style={{ maxWidth: '460px', width: '100%' }}>
          {/* Branding */}
          <div style={{ textAlign: 'center', marginBottom: '24px' }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <div className="logo-mark__icon" style={{ width: '36px', height: '36px' }}>
                <Compass size={19} />
              </div>
              <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: '1.3rem', letterSpacing: '-0.02em' }}>
                Career Beacon
              </span>
            </div>
            <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
              Labor-market skill calibration &amp; verified industry mentorship
            </p>
          </div>

          {/* Auth Card */}
          <div className="card" style={{ padding: '32px 28px', boxShadow: 'var(--shadow-md)' }}>
            {/* Card Header */}
            <div style={{ marginBottom: '20px' }}>
              <h2 style={{ fontSize: '1.3rem', marginBottom: '6px' }}>
                {isRecovery
                  ? 'Set a New Password'
                  : isSignUp
                  ? `Create ${role === 'mentor' ? 'Mentor' : 'Learner'} Account`
                  : 'Sign in to Career Beacon'}
              </h2>
              <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                {isRecovery
                  ? 'Enter and confirm your new password below.'
                  : isSignUp
                  ? role === 'mentor'
                    ? 'Connect with learners, answer domain Q&As, and host 1-on-1 sessions.'
                    : 'Map your capabilities against occupational taxonomies and start learning sprints.'
                  : 'Access your career roadmap, learning sprints, and mentorship sessions.'}
              </p>
            </div>

            {/* Role Selector on Sign Up */}
            {isSignUp && !isRecovery && (
              <div
                role="group"
                aria-label="Account role"
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '6px',
                  background: 'var(--surface-elevated)',
                  padding: '4px',
                  borderRadius: 'var(--r-md)',
                  marginBottom: '20px',
                  border: '1px solid var(--border)',
                }}
              >
                <button
                  type="button"
                  className={`btn btn--sm ${role === 'learner' ? 'btn--primary' : 'btn--ghost'}`}
                  onClick={() => {
                    setRole('learner');
                    setStatus('Student');
                  }}
                  style={{ border: 'none' }}
                >
                  <GraduationCap size={15} />
                  <span>Learner</span>
                </button>
                <button
                  type="button"
                  className={`btn btn--sm ${role === 'mentor' ? 'btn--primary' : 'btn--ghost'}`}
                  onClick={() => {
                    setRole('mentor');
                    setStatus('Industry Mentor');
                  }}
                  style={{ border: 'none' }}
                >
                  <Users size={15} />
                  <span>Mentor</span>
                </button>
              </div>
            )}

            {/* RECOVERY MODE FORM */}
            {isRecovery ? (
              <form onSubmit={handleCompletePasswordReset} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <label htmlFor="recovery-new-password" style={{ display: 'block', marginBottom: '6px' }}>
                    New Password
                  </label>
                  <div style={{ position: 'relative' }}>
                    <input
                      id="recovery-new-password"
                      type={showNewPassword ? 'text' : 'password'}
                      placeholder="At least 6 characters"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      required
                      minLength={6}
                      style={{ paddingRight: '42px' }}
                    />
                    <button
                      type="button"
                      aria-label={showNewPassword ? 'Hide password' : 'Show password'}
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
                        display: 'inline-flex',
                        padding: '4px',
                      }}
                    >
                      {showNewPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {newPassword && (
                    <div style={{ marginTop: '8px' }}>
                      <div style={{ display: 'flex', gap: '4px', height: '4px', marginBottom: '4px' }}>
                        {[1, 2, 3].map((step) => (
                          <div
                            key={step}
                            style={{
                              flex: 1,
                              borderRadius: '2px',
                              background: pwdStrength?.score >= step ? pwdStrength.color : 'var(--border)',
                              transition: 'background 0.2s',
                            }}
                          />
                        ))}
                      </div>
                      <span style={{ fontSize: '0.74rem', color: pwdStrength?.color, fontWeight: 600 }}>
                        Strength: {pwdStrength?.label}
                      </span>
                    </div>
                  )}
                </div>

                <div>
                  <label htmlFor="recovery-confirm-password" style={{ display: 'block', marginBottom: '6px' }}>
                    Confirm New Password
                  </label>
                  <input
                    id="recovery-confirm-password"
                    type={showNewPassword ? 'text' : 'password'}
                    placeholder="Repeat new password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                  />
                  {confirmPassword && (
                    <span
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 500,
                        display: 'block',
                        marginTop: '4px',
                        color: newPassword === confirmPassword ? 'var(--status-success)' : 'var(--status-danger)',
                      }}
                    >
                      {newPassword === confirmPassword ? 'Passwords match' : 'Passwords do not match'}
                    </span>
                  )}
                </div>

                <button type="submit" className="btn btn--primary btn--full" disabled={loading} style={{ marginTop: '4px' }}>
                  {loading ? 'Updating Password...' : 'Save New Password'}
                </button>
              </form>
            ) : (
              /* STANDARD SIGN-IN & SIGN-UP FORM */
              <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                {isSignUp && (
                  <>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                      <div>
                        <label htmlFor="signup-first-name" style={{ display: 'block', marginBottom: '6px' }}>
                          First Name
                        </label>
                        <input
                          id="signup-first-name"
                          type="text"
                          placeholder="Alex"
                          value={firstName}
                          onChange={(e) => setFirstName(e.target.value)}
                          required
                        />
                      </div>
                      <div>
                        <label htmlFor="signup-last-name" style={{ display: 'block', marginBottom: '6px' }}>
                          Last Name
                        </label>
                        <input
                          id="signup-last-name"
                          type="text"
                          placeholder="Kim"
                          value={lastName}
                          onChange={(e) => setLastName(e.target.value)}
                          required
                        />
                      </div>
                    </div>

                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <label htmlFor="signup-username">Username</label>
                        {usernameMsg && (
                          <span
                            style={{
                              fontSize: '0.75rem',
                              fontWeight: 600,
                              color:
                                usernameStatus === 'available'
                                  ? 'var(--status-success)'
                                  : usernameStatus === 'taken' || usernameStatus === 'invalid'
                                  ? 'var(--status-danger)'
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
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          @
                        </span>
                        <input
                          id="signup-username"
                          type="text"
                          placeholder="alex_kim"
                          value={username}
                          onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                          required
                          minLength={3}
                          maxLength={25}
                          style={{ paddingLeft: '28px' }}
                        />
                      </div>
                    </div>

                    {role === 'learner' && (
                      <div>
                        <label htmlFor="signup-status-headline" style={{ display: 'block', marginBottom: '6px' }}>
                          Professional Status
                        </label>
                        <select
                          id="signup-status-headline"
                          value={status}
                          onChange={(e) => setStatus(e.target.value)}
                        >
                          <option value="Student">Student / Recent Graduate</option>
                          <option value="Working Professional">Working Professional / Career Changer</option>
                          <option value="Self-Taught">Self-Taught Practitioner / Independent</option>
                        </select>
                      </div>
                    )}
                  </>
                )}

                {/* Email or Username */}
                <div>
                  <label htmlFor="auth-email" style={{ display: 'block', marginBottom: '6px' }}>
                    {isSignUp ? 'Email Address' : 'Email Address or Username'}
                  </label>
                  <input
                    id="auth-email"
                    type={isSignUp ? 'email' : 'text'}
                    placeholder={isSignUp ? 'name@organization.com' : 'name@organization.com or @username'}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete={isSignUp ? 'email' : 'username'}
                  />
                </div>

                {/* Password */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <label htmlFor="auth-password">Password</label>
                    {!isSignUp && (
                      <button
                        type="button"
                        onClick={handleResetPassword}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--accent)',
                          fontSize: '0.78rem',
                          fontWeight: 600,
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
                      id="auth-password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Enter password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={6}
                      autoComplete={isSignUp ? 'new-password' : 'current-password'}
                      style={{ paddingRight: '42px' }}
                    />
                    <button
                      type="button"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
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
                        display: 'inline-flex',
                        padding: '4px',
                      }}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>

                  {isSignUp && password && (
                    <div style={{ marginTop: '8px' }}>
                      <div style={{ display: 'flex', gap: '4px', height: '4px', marginBottom: '4px' }}>
                        {[1, 2, 3].map((step) => (
                          <div
                            key={step}
                            style={{
                              flex: 1,
                              borderRadius: '2px',
                              background: pwdStrength.score >= step ? pwdStrength.color : 'var(--border)',
                              transition: 'background 0.2s',
                            }}
                          />
                        ))}
                      </div>
                      <span style={{ fontSize: '0.74rem', color: pwdStrength.color, fontWeight: 600 }}>
                        Strength: {pwdStrength.label}
                      </span>
                    </div>
                  )}
                </div>

                <button
                  type="submit"
                  className="btn btn--primary btn--full"
                  disabled={loading}
                  style={{ marginTop: '4px' }}
                >
                  {loading ? (
                    <>
                      <span className="spinner" style={{ width: '16px', height: '16px' }} />
                      <span>{isSignUp ? 'Creating account...' : 'Signing in...'}</span>
                    </>
                  ) : isSignUp ? (
                    `Create ${role === 'mentor' ? 'Mentor' : 'Learner'} Account`
                  ) : (
                    'Sign In'
                  )}
                </button>

                {/* OAuth Separator */}
                <div className="divider">Or continue with</div>

                {/* OAuth Providers */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <button
                    type="button"
                    className="btn btn--secondary btn--sm"
                    onClick={() => handleSocialLogin('google')}
                    disabled={loading}
                    title="Continue with Google"
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" aria-hidden="true">
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
                    <span>Google</span>
                  </button>

                  <button
                    type="button"
                    className="btn btn--secondary btn--sm"
                    onClick={() => handleSocialLogin('github')}
                    disabled={loading}
                    title="Continue with GitHub"
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                      <path d="M12 2A10 10 0 0 0 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.1-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0 0 12 2Z" />
                    </svg>
                    <span>GitHub</span>
                  </button>
                </div>

                {/* Mode switch */}
                <p style={{ textAlign: 'center', marginTop: '8px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
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
                      color: 'var(--accent)',
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
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-secondary)',
                textDecoration: 'underline',
                cursor: 'pointer',
                padding: 0,
              }}
            >
              Terms of Service
            </button>{' '}
            and{' '}
            <button
              type="button"
              onClick={() => setActiveModal('privacy')}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-secondary)',
                textDecoration: 'underline',
                cursor: 'pointer',
                padding: 0,
              }}
            >
              Privacy Policy
            </button>
            .
          </p>
        </div>
      </div>

      {/* Terms / Privacy Modal */}
      {activeModal && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'var(--backdrop)',
            backdropFilter: 'blur(2px)',
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
            style={{ maxWidth: '500px', width: '100%', padding: '24px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h3>{activeModal === 'terms' ? 'Terms of Service' : 'Privacy Policy'}</h3>
              <button
                type="button"
                aria-label="Close dialog"
                className="btn btn--ghost btn--xs"
                onClick={() => setActiveModal(null)}
              >
                <X size={15} />
              </button>
            </div>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.65, marginBottom: '20px' }}>
              {activeModal === 'terms'
                ? 'Career Beacon is an educational platform providing labor-market skill calibration, micro-learning sprints, and verified mentorship sessions. By registering, you agree to uphold academic integrity and respect mentor availability.'
                : 'Your profile data and assessment scores are protected and never distributed to third parties. Semantic vector embeddings are stored securely via Supabase pgvector.'}
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
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
    </div>
  );
}
