// src/App.jsx
import { useState, useEffect, useRef } from 'react';
import { supabase } from './lib/SupabaseClient';
import { getOnboardingStatus } from './lib/api';
import Landing from './pages/Landing';
import Login from './pages/Login';
import LearnerOnboarding from './pages/LearnerOnboarding';
import MentorOnboarding from './pages/MentorOnboarding';
import MentorDashboard from './pages/MentorDashboard';
import Dashboard from './pages/Dashboard';
import AdminPortal from './pages/AdminPortal';
import { AlertTriangle, Compass, CheckCircle2, RefreshCw } from './components/Icons';

function checkIsRecoveryUrl() {
  const hash = window.location.hash || '';
  const search = window.location.search || '';
  return hash.includes('type=recovery') || search.includes('type=recovery');
}

// App-level state machine:
// 'loading' | 'landing' | 'auth' | 'recovery' | 'onboarding' | 'mentor_onboarding' | 'dashboard'
export default function App() {
  const [appState, setAppState] = useState(() => (checkIsRecoveryUrl() ? 'recovery' : 'loading'));
  const [authConfig, setAuthConfig] = useState({ mode: 'signin', role: 'learner' });
  const [user, setUser] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [career, setCareer] = useState(null);
  const [skills, setSkills] = useState([]);

  // Track recovery mode in ref to immediately block any async bootstrap race condition
  const isRecoveryRef = useRef(checkIsRecoveryUrl());
  const bootstrappedUserIdRef = useRef(null);
  const [isRecovery, setIsRecovery] = useState(checkIsRecoveryUrl());
  const [isOffline, setIsOffline] = useState(() => (typeof navigator !== 'undefined' ? !navigator.onLine : false));
  const [showOnlineToast, setShowOnlineToast] = useState(false);
  const [checkingNetwork, setCheckingNetwork] = useState(false);

  useEffect(() => {
    let onlineTimer = null;
    const handleOnline = () => {
      setIsOffline(false);
      setShowOnlineToast(true);
      if (onlineTimer) clearTimeout(onlineTimer);
      onlineTimer = setTimeout(() => {
        setShowOnlineToast(false);
      }, 4000);
    };
    const handleOffline = () => {
      setIsOffline(true);
      setShowOnlineToast(false);
    };
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      if (onlineTimer) clearTimeout(onlineTimer);
    };
  }, []);

  const handleManualNetworkCheck = async () => {
    setCheckingNetwork(true);
    try {
      if (!navigator.onLine) {
        setIsOffline(true);
      } else {
        const ping = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/admin/stats`, {
          method: 'HEAD',
          cache: 'no-store',
        }).catch(() => null);
        if (ping) {
          setIsOffline(false);
          setShowOnlineToast(true);
          setTimeout(() => setShowOnlineToast(false), 4000);
        } else {
          setIsOffline(!navigator.onLine);
        }
      }
    } catch {
      setIsOffline(!navigator.onLine);
    } finally {
      setCheckingNetwork(false);
    }
  };

  useEffect(() => {
    const bootstrap = async (session) => {
      if (isRecoveryRef.current || checkIsRecoveryUrl()) {
        setAppState('recovery');
        return;
      }

      if (!session?.user) {
        bootstrappedUserIdRef.current = null;
        setUser(null);
        setUserProfile(null);
        setCareer(null);
        setSkills([]);
        setAppState('landing');
        return;
      }

      // If this exact user is already bootstrapped, do NOT reset appState to 'loading'
      // when Supabase fires TOKEN_REFRESHED or SIGNED_IN on browser tab focus.
      if (bootstrappedUserIdRef.current === session.user.id) {
        setUser(session.user);
        return;
      }

      bootstrappedUserIdRef.current = session.user.id;
      setUser(session.user);
      setAppState('loading');

      try {
        // Fetch profile for role-based routing (learner vs mentor)
        const { data: profile } = await supabase
          .from('profiles')
          .select('*')
          .eq('id', session.user.id)
          .maybeSingle();

        // Cross-reference mentors table directly as the definitive source of truth
        const { data: mentorData } = await supabase
          .from('mentors')
          .select('id, profile_id, bio, expertise')
          .eq('profile_id', session.user.id)
          .maybeSingle();

        const userEmail = (session.user?.email || '').toLowerCase();
        const rawRole = session.user?.user_metadata?.role || profile?.role;
        const isMentor =
          rawRole === 'mentor' ||
          Boolean(mentorData?.id) ||
          userEmail.startsWith('mentor') ||
          (profile?.full_name || '').toLowerCase().includes('mentor');

        const userRole = isMentor ? 'mentor' : (rawRole || 'learner');
        const resolvedProfile = profile ? { ...profile, role: userRole } : { id: session.user.id, role: userRole };
        setUserProfile(resolvedProfile);

        const isAdmin = userRole === 'admin' || userEmail.startsWith('admin@') || window.location.pathname === '/admin';

        if (isAdmin) {
          setAppState('admin_portal');
          return;
        }

        // Self-heal profile.role if missing in profiles table
        if (isMentor && profile && profile.role !== 'mentor') {
          supabase.from('profiles').update({ role: 'mentor' }).eq('id', session.user.id).then(() => {});
        }

        if (isMentor) {
          if ((mentorData?.id && mentorData?.bio) || (profile?.bio && profile.bio.length >= 10)) {
            setAppState('dashboard');
          } else {
            setAppState('mentor_onboarding');
          }
          return;
        }

        // Learner workflow: check onboarding status
        const status = await getOnboardingStatus(session.user.id);
        if (isRecoveryRef.current || checkIsRecoveryUrl()) {
          setAppState('recovery');
          return;
        }

        if (status.onboarding_complete) {
          setCareer(status.career);
          setSkills(status.skills);
          setAppState('dashboard');
        } else {
          setAppState('onboarding');
        }
      } catch (err) {
        if (isRecoveryRef.current || checkIsRecoveryUrl()) {
          setAppState('recovery');
          return;
        }
        console.error('Failed to resolve user routing:', err);
        const fallbackRole = session.user?.user_metadata?.role || 'learner';
        setAppState(fallbackRole === 'mentor' ? 'mentor_onboarding' : 'onboarding');
      }
    };

    // Subscribe to Supabase auth events
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'PASSWORD_RECOVERY') {
        isRecoveryRef.current = true;
        setIsRecovery(true);
        setAppState('recovery');
        return;
      }

      if (isRecoveryRef.current || checkIsRecoveryUrl()) {
        setAppState('recovery');
        return;
      }

      bootstrap(session);
    });

    // Hydrate current session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (isRecoveryRef.current || checkIsRecoveryUrl()) {
        setAppState('recovery');
        return;
      }
      bootstrap(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleSelectRole = (selectedRole) => {
    setAuthConfig({ mode: 'signup', role: selectedRole });
    setAppState('auth');
  };

  const handleSignInClick = () => {
    setAuthConfig({ mode: 'signin', role: 'learner' });
    setAppState('auth');
  };

  const handleBackToLanding = () => {
    setAppState('landing');
  };

  const handleOnboardingComplete = ({ career: c, skills: s }) => {
    setCareer(c);
    setSkills(s);
    setAppState('dashboard');
  };

  const handleSkillUpdated = ({ skillId, newProficiency }) => {
    setSkills((prev) =>
      prev.map((s) => (s.id === skillId ? { ...s, proficiency: newProficiency } : s))
    );
  };

  const handleRecoveryComplete = () => {
    isRecoveryRef.current = false;
    setIsRecovery(false);
    setUser(null);
    setAuthConfig({ mode: 'signin', role: 'learner' });
    setAppState('auth');
  };

  const renderContent = () => {
    // 1. Loading View
    if (appState === 'loading') {
      return (
        <div
          style={{
            minHeight: '100svh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            gap: '14px',
            background: 'var(--background)',
          }}
        >
          <div className="logo-mark__icon" style={{ width: '40px', height: '40px' }}>
            <Compass size={20} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: 500 }}>
            <div className="spinner" />
            <span>Loading Career Beacon workspace...</span>
          </div>
        </div>
      );
    }

    // 2. Password Recovery View (highest priority)
    if (appState === 'recovery' || isRecovery) {
      return (
        <Login
          initialMode="recovery"
          onRecoveryComplete={handleRecoveryComplete}
          onBackToLanding={handleBackToLanding}
        />
      );
    }

    // 3. Unauthenticated Landing View
    if (appState === 'landing') {
      return (
        <Landing
          onSelectRole={handleSelectRole}
          onSignIn={handleSignInClick}
        />
      );
    }

    // 4. Auth View (Sign In or Sign Up with role metadata)
    if (appState === 'auth') {
      return (
        <Login
          initialMode={authConfig.mode}
          targetRole={authConfig.role}
          onBackToLanding={handleBackToLanding}
          onRecoveryComplete={handleRecoveryComplete}
        />
      );
    }

    // 5a. Mentor Onboarding
    if (appState === 'mentor_onboarding') {
      return (
        <MentorOnboarding
          user={user}
          userProfile={userProfile}
          onComplete={async () => {
            setUserProfile((prev) => ({ ...(prev || {}), role: 'mentor' }));
            if (user?.id) {
              const { data: refreshedProfile } = await supabase
                .from('profiles')
                .select('*')
                .eq('id', user.id)
                .maybeSingle();
              if (refreshedProfile) {
                setUserProfile({ ...refreshedProfile, role: 'mentor' });
              }
            }
            setAppState('dashboard');
          }}
        />
      );
    }

    // 5b. Learner Onboarding
    if (appState === 'onboarding') {
      return <LearnerOnboarding user={user} onComplete={handleOnboardingComplete} />;
    }

    // 5c. Admin Command Center
    if (appState === 'admin_portal') {
      return (
        <AdminPortal
          user={user}
          onSignOut={() => {
            setAppState('landing');
            setUser(null);
            setUserProfile(null);
          }}
        />
      );
    }

    // 6. Main Dashboard View (Mentor Workspace vs Learner Dashboard)
    const userEmailStr = (user?.email || '').toLowerCase();
    const effectiveRole =
      userProfile?.role === 'mentor' ||
      user?.user_metadata?.role === 'mentor' ||
      userEmailStr.startsWith('mentor') ||
      (userProfile?.full_name || '').toLowerCase().includes('mentor')
        ? 'mentor'
        : (userProfile?.role || user?.user_metadata?.role || 'learner');
    if (effectiveRole === 'mentor') {
      return (
        <MentorDashboard
          user={user}
          userProfile={userProfile}
          onRecalibrateCareer={() => setAppState('mentor_onboarding')}
        />
      );
    }

    return (
      <Dashboard
        user={user}
        userProfile={userProfile}
        career={career}
        skills={skills}
        onSkillUpdated={handleSkillUpdated}
        onRecalibrateCareer={() => setAppState('onboarding')}
      />
    );
  };

  return (
    <>
      {isOffline && (
        <div
          role="alert"
          style={{
            background: 'var(--status-danger-bg)',
            color: 'var(--status-danger)',
            borderBottom: '1px solid var(--status-danger-bd)',
            padding: '10px 16px',
            fontSize: '0.84rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px',
            position: 'sticky',
            top: 0,
            zIndex: 10000,
            boxShadow: 'var(--shadow-sm)',
            flexWrap: 'wrap',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={16} />
            <span>Connection dropped. Actions requiring server response will resume once reconnected.</span>
          </div>
          <button
            type="button"
            className="btn btn--ghost btn--xs"
            onClick={handleManualNetworkCheck}
            disabled={checkingNetwork}
            style={{
              padding: '2px 8px',
              fontSize: '0.75rem',
              color: 'var(--status-danger)',
              border: '1px solid var(--status-danger-bd)',
              borderRadius: 'var(--r-sm)',
            }}
          >
            <RefreshCw size={12} className={checkingNetwork ? 'spinning' : ''} />
            <span>{checkingNetwork ? 'Checking...' : 'Retry Connection'}</span>
          </button>
        </div>
      )}

      {showOnlineToast && !isOffline && (
        <div
          role="status"
          className="animate-fade-in"
          style={{
            background: 'var(--status-success-bg)',
            color: 'var(--status-success)',
            borderBottom: '1px solid var(--status-success-bd)',
            padding: '8px 16px',
            fontSize: '0.84rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            position: 'sticky',
            top: 0,
            zIndex: 10000,
          }}
        >
          <CheckCircle2 size={16} />
          <span>Internet connection restored. You are back online!</span>
        </div>
      )}
      {renderContent()}
    </>
  );
}
