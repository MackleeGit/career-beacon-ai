// src/App.jsx
import { useState, useEffect, useRef } from 'react';
import { supabase } from './lib/SupabaseClient';
import { getOnboardingStatus } from './lib/api';
import Login from './pages/Login';
import Onboarding from './pages/Onboarding';
import Dashboard from './pages/Dashboard';

function checkIsRecoveryUrl() {
  const hash = window.location.hash || '';
  const search = window.location.search || '';
  return hash.includes('type=recovery') || search.includes('type=recovery');
}

// App-level state machine: 'loading' | 'unauthenticated' | 'recovery' | 'onboarding' | 'dashboard'
export default function App() {
  const [appState, setAppState] = useState('loading');
  const [user, setUser]         = useState(null);
  const [career, setCareer]     = useState(null);
  const [skills, setSkills]     = useState([]);
  
  // Track recovery mode in ref to immediately block any async bootstrap race condition
  const isRecoveryRef = useRef(checkIsRecoveryUrl());
  const [isRecovery, setIsRecovery] = useState(checkIsRecoveryUrl());

  useEffect(() => {
    // If the page was loaded with a recovery URL, immediately force recovery state
    if (checkIsRecoveryUrl()) {
      isRecoveryRef.current = true;
      setIsRecovery(true);
      setAppState('recovery');
    }

    const bootstrap = async (session) => {
      // Guard: Never bootstrap into onboarding or dashboard if actively in recovery mode!
      if (isRecoveryRef.current || checkIsRecoveryUrl()) {
        setAppState('recovery');
        return;
      }

      if (!session?.user) {
        setUser(null);
        setCareer(null);
        setSkills([]);
        setAppState('unauthenticated');
        return;
      }

      setUser(session.user);

      try {
        const status = await getOnboardingStatus(session.user.id);
        // Double-check guard before setting state in case recovery event fired while fetching
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
        console.error('Failed to fetch onboarding status:', err);
        setAppState('onboarding');
      }
    };

    // Subscribe to auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'PASSWORD_RECOVERY') {
        isRecoveryRef.current = true;
        setIsRecovery(true);
        setAppState('recovery');
        return;
      }

      // If in recovery mode, ignore general SIGNED_IN events so we don't jump to Onboarding
      if (isRecoveryRef.current || checkIsRecoveryUrl()) {
        setAppState('recovery');
        return;
      }

      bootstrap(session);
    });

    // Hydrate from current session on mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (isRecoveryRef.current || checkIsRecoveryUrl()) {
        setAppState('recovery');
        return;
      }
      bootstrap(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  // Called by Onboarding when skills are saved
  const handleOnboardingComplete = ({ career: c, skills: s }) => {
    setCareer(c);
    setSkills(s);
    setAppState('dashboard');
  };

  // Called when a micro-learning quiz is passed
  const handleSkillUpdated = ({ skillId, newProficiency }) => {
    setSkills((prev) =>
      prev.map((s) => (s.id === skillId ? { ...s, proficiency: newProficiency } : s))
    );
  };

  const handleRecoveryComplete = () => {
    isRecoveryRef.current = false;
    setIsRecovery(false);
    setUser(null);
    setAppState('unauthenticated');
  };

  // Render view based on app state
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

  // Password recovery always takes precedence over onboarding/dashboard
  if (appState === 'recovery' || isRecovery) {
    return (
      <Login
        initialMode="recovery"
        onRecoveryComplete={handleRecoveryComplete}
      />
    );
  }

  if (appState === 'unauthenticated') {
    return <Login onRecoveryComplete={handleRecoveryComplete} />;
  }

  if (appState === 'onboarding') {
    return <Onboarding user={user} onComplete={handleOnboardingComplete} />;
  }

  return (
    <Dashboard
      user={user}
      career={career}
      skills={skills}
      onSkillUpdated={handleSkillUpdated}
    />
  );
}
