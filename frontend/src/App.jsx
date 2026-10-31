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

  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

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

        setUserProfile(profile);

        if (profile?.role === 'mentor') {
          // Mentor workflow: check if mentor has completed onboarding in `mentors` table
          const { data: mentorData } = await supabase
            .from('mentors')
            .select('id, profile_id, bio, expertise')
            .eq('profile_id', session.user.id)
            .maybeSingle();

          if (mentorData?.id && mentorData?.bio) {
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
        setAppState('onboarding');
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
            gap: '16px',
            background: 'var(--bg-base)',
          }}
        >
          <div className="spinner spinner--lg" />
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Loading Career Beacon...</p>
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
          onComplete={() => setAppState('dashboard')}
        />
      );
    }

    // 5b. Learner Onboarding
    if (appState === 'onboarding') {
      return <LearnerOnboarding user={user} onComplete={handleOnboardingComplete} />;
    }

    // 6. Main Dashboard View (Mentor Workspace vs Learner Dashboard)
    if (userProfile?.role === 'mentor') {
      return (
        <MentorDashboard
          user={user}
          userProfile={userProfile}
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
      />
    );
  };

  return (
    <>
      {isOffline && (
        <div
          role="alert"
          style={{
            background: 'hsl(0, 75%, 45%)',
            color: '#fff',
            padding: '10px 16px',
            fontSize: '0.85rem',
            fontWeight: 600,
            textAlign: 'center',
            position: 'sticky',
            top: 0,
            zIndex: 10000,
            boxShadow: '0 2px 10px rgba(0,0,0,0.3)',
          }}
        >
          ⚠️ No internet connection detected. Career Beacon will automatically reconnect once your connection is restored.
        </div>
      )}
      {renderContent()}
    </>
  );
}
