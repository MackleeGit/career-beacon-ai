// src/App.jsx
import { useState, useEffect } from 'react';
import { supabase } from './lib/SupabaseClient';
import { getOnboardingStatus } from './lib/api';
import Login from './pages/Login';
import Onboarding from './pages/Onboarding';
import Dashboard from './pages/Dashboard';

// App-level state machine: 'loading' | 'unauthenticated' | 'onboarding' | 'dashboard'
export default function App() {
  const [appState, setAppState] = useState('loading');
  const [user, setUser]         = useState(null);
  const [career, setCareer]     = useState(null);
  const [skills, setSkills]     = useState([]);

  // ── Bootstrapper: runs when auth state changes ──────────────────────────────
  useEffect(() => {
    const bootstrap = async (session) => {
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
        if (status.onboarding_complete) {
          setCareer(status.career);
          setSkills(status.skills);
          setAppState('dashboard');
        } else {
          setAppState('onboarding');
        }
      } catch (err) {
        // If the backend is offline, still show onboarding rather than a blank screen
        console.error('Failed to fetch onboarding status:', err);
        setAppState('onboarding');
      }
    };

    // Subscribe to auth changes (handles login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      bootstrap(session);
    });

    // Hydrate from current session on mount
    supabase.auth.getSession().then(({ data: { session } }) => bootstrap(session));

    return () => subscription.unsubscribe();
  }, []);

  // ── Called by Onboarding when skills are saved ──────────────────────────────
  const handleOnboardingComplete = ({ career: c, skills: s }) => {
    setCareer(c);
    setSkills(s);
    setAppState('dashboard');
  };

  // ── Render ───────────────────────────────────────────────────────────────────
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
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Loading Career Beacon…</p>
      </div>
    );
  }

  if (appState === 'unauthenticated') return <Login />;

  if (appState === 'onboarding') {
    return <Onboarding user={user} onComplete={handleOnboardingComplete} />;
  }

  return <Dashboard user={user} career={career} skills={skills} />;
}
