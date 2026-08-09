import { useState, useEffect } from 'react';
import React from 'react';
import { supabase } from '../lib/SupabaseClient';
import ErrorBoundary from '../components/ErrorBoundary';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [msg, setMsg] = useState(null);

  // Verify Supabase env vars are present
  useEffect(() => {
    if (!import.meta.env.VITE_SUPABASE_URL || !import.meta.env.VITE_SUPABASE_ANON_KEY) {
      console.error('Supabase configuration missing');
      setMsg('⚠️ Supabase environment variables not set. Check .env file.');
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMsg(null);
    try {
      if (isSignUp) {
        // Sign‑up flow – creates a user in auth.users, then inserts a profile row manually
        const { data, error: signUpError } = await supabase.auth.signUp({
          email,
          password,
        });
        if (signUpError) throw signUpError;
        // Insert a profile for the newly created user (if not already inserted by a trigger)
        if (data?.user) {
          const { error: profileError } = await supabase.from('profiles').insert({
            id: data.user.id,
            email: data.user.email,
          });
          if (profileError) throw profileError;
        }
        setMsg('✅ Sign‑up successful – check your email for verification.');
      } else {
        // Sign‑in flow – retrieves the existing session
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        setMsg('✅ Signed in!');
      }
    } catch (err) {
      console.error('Auth error:', err);
      setMsg(`❌ ${err.message || 'Authentication failed'}`);
    }
  };

  return (
    <ErrorBoundary>
      <div className="login" style={{ maxWidth: '320px', margin: '2rem auto', padding: '1rem', border: '1px solid #ddd', borderRadius: '8px' }}>
        <h2>{isSignUp ? 'Create an account' : 'Sign in'}</h2>
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ width: '100%', marginBottom: '0.5rem', padding: '0.5rem' }}
          />
          <input
            type="password"
            placeholder="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ width: '100%', marginBottom: '0.5rem', padding: '0.5rem' }}
          />
          <button type="submit" style={{ width: '100%', padding: '0.5rem' }}>
            {isSignUp ? 'Sign up' : 'Sign in'}
          </button>
        </form>
        <p style={{ marginTop: '1rem' }}>
          {isSignUp ? 'Already have an account? ' : "Don't have an account? "}
          <button
            onClick={() => {
              setIsSignUp(!isSignUp);
              setMsg(null);
            }}
            style={{ background: 'none', border: 'none', color: '#0066cc', textDecoration: 'underline', cursor: 'pointer' }}
          >
            {isSignUp ? 'Log in' : 'Register'}
          </button>
        </p>
        {msg && <p>{msg}</p>}
      </div>
    </ErrorBoundary>
  );
}
