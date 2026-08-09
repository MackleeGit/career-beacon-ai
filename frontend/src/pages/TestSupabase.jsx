import { useEffect, useState } from 'react';
import { supabase } from '../lib/SupabaseClient';

export default function TestSupabase() {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchProfile = async () => {
      // Get the current authenticated user (new Supabase auth API)
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        setError('User not signed in');
        return;
      }
      const { data, error } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', user.id)
        .single();

      if (error) setError(error.message);
      else setProfile(data);
    };
    fetchProfile();
  }, []);

  return (
    <div style={{ padding: '1rem' }}>
      <h2>Supabase sanity check</h2>
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
      {profile ? (
        <pre>{JSON.stringify(profile, null, 2)}</pre>
      ) : (
        <p>No profile loaded – try signing in first.</p>
      )}
    </div>
  );
}
