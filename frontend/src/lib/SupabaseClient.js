// src/lib/SupabaseClient.js
import { createClient } from '@supabase/supabase-js';

// Vite automatically injects any environment variable that starts with VITE_
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// Export a singleton client for the whole app
export const supabase = createClient(supabaseUrl, supabaseAnonKey);
