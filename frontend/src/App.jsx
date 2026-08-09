// src/App.jsx – Home component (re‑styled)
import { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';
import reactLogo from './assets/react.svg';
import viteLogo from './assets/vite.svg';
import heroImg from './assets/hero.png';
import './App.css';
import TestSupabase from './pages/TestSupabase';
import Login from './pages/Login';
import { supabase } from './lib/SupabaseClient';

function App() {
  const [user, setUser] = useState(null);
  useEffect(() => {
    // Listen for auth changes using the subscription object
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    // Check current session on mount
    supabase.auth.getUser().then(({ data: { user } }) => setUser(user));
    return () => {
      subscription.unsubscribe();
    };
  }, []);
  return (
    <div className="container">
      {user ? <TestSupabase /> : <Login />}
    </div>
  );
}
export default App;
