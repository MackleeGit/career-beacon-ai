// src/lib/SupabaseClient.js
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// Central environment configuration validation
if (!supabaseUrl || !supabaseAnonKey) {
  console.error(
    '[SupabaseClient] Missing Supabase configuration. Ensure VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are set in frontend/.env'
  );
}

// Export a single shared singleton client instance with standard auth persistence
export const supabase = createClient(supabaseUrl || '', supabaseAnonKey || '', {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true, // Enables automatic parsing of recovery tokens & PKCE codes
  },
});
