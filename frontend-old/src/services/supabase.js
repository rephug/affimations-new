// src/services/supabase.js
import { createClient } from '@supabase/supabase-js';

// Initialize Supabase client
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Check if values are available
if (!supabaseUrl || !supabaseAnonKey) {
  console.error(
    'Missing Supabase environment variables. Check your .env file.'
  );
}


// Authentication helpers
export const signUpWithEmail = async (email, password, metadata = {}) => {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: metadata
    }
  });
  return { data, error };
};

export const signInWithEmail = async (email, password) => {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password
  });
  return { data, error };
};

export const signInWithProvider = async (provider) => {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider
  });
  return { data, error };
};

export const signOut = async () => {
  const { error } = await supabase.auth.signOut();
  return { error };
};

export const getCurrentUser = async () => {
  const { data: { user } } = await supabase.auth.getUser();
  return user;
};

export const resetPassword = async (email) => {
  const { data, error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${window.location.origin}/reset-password`
  });
  return { data, error };
};

export const updatePassword = async (newPassword) => {
  const { data, error } = await supabase.auth.updateUser({
    password: newPassword
  });
  return { data, error };
};

// User profile helpers
export const getProfile = async (userId) => {
  const { data, error } = await supabase
    .from('profiles')
    .select('*')
    .eq('id', userId)
    .single();
  
  return { data, error };
};

export const createProfile = async (profile) => {
  const { data, error } = await supabase
    .from('profiles')
    .insert([profile])
    .select();
  
  return { data, error };
};

export const updateProfile = async (userId, updates) => {
  const { data, error } = await supabase
    .from('profiles')
    .update(updates)
    .eq('id', userId)
    .select();
  
  return { data, error };
};

// Affirmations helpers
export const getAffirmations = async (options = {}) => {
  let query = supabase
    .from('affirmations')
    .select('*');
  
  // Add filters
  if (options.category) {
    query = query.eq('category', options.category);
  }
  
  if (options.isPublic !== undefined) {
    query = query.eq('is_public', options.isPublic);
  }
  
  if (options.userId) {
    query = query.eq('created_by', options.userId);
  } else {
    // If no user ID provided, only show public affirmations
    query = query.eq('is_public', true);
  }
  
  // Add sorting
  if (options.orderBy) {
    query = query.order(options.orderBy, { ascending: options.ascending ?? true });
  }
  
  // Add pagination
  if (options.limit) {
    query = query.limit(options.limit);
  }
  
  if (options.offset) {
    query = query.range(options.offset, options.offset + (options.limit || 10) - 1);
  }
  
  const { data, error } = await query;
  return { data, error };
};

export const createAffirmation = async (affirmation) => {
  const { data, error } = await supabase
    .from('affirmations')
    .insert([affirmation])
    .select();
  
  return { data, error };
};

export const updateAffirmation = async (id, updates) => {
  const { data, error } = await supabase
    .from('affirmations')
    .update(updates)
    .eq('id', id)
    .select();
  
  return { data, error };
};

export const deleteAffirmation = async (id) => {
  const { data, error } = await supabase
    .from('affirmations')
    .delete()
    .eq('id', id);
  
  return { data, error };
};

// Scheduled calls helpers
export const getScheduledCalls = async (userId) => {
  const { data, error } = await supabase
    .from('scheduled_calls')
    .select('*')
    .eq('user_id', userId);
  
  return { data, error };
};

export const createScheduledCall = async (scheduledCall) => {
  const { data, error } = await supabase
    .from('scheduled_calls')
    .insert([scheduledCall])
    .select();
  
  return { data, error };
};

export const updateScheduledCall = async (id, updates) => {
  const { data, error } = await supabase
    .from('scheduled_calls')
    .update(updates)
    .eq('id', id)
    .select();
  
  return { data, error };
};

export const deleteScheduledCall = async (id) => {
  const { data, error } = await supabase
    .from('scheduled_calls')
    .delete()
    .eq('id', id);
  
  return { data, error };
};

// Call history helpers
export const getCallHistory = async (userId, options = {}) => {
  let query = supabase
    .from('call_history')
    .select('*, transcriptions(*)')
    .eq('user_id', userId);
  
  // Add sorting (default: most recent first)
  query = query.order(
    options.orderBy || 'started_at', 
    { ascending: options.ascending ?? false }
  );
  
  // Add pagination
  if (options.limit) {
    query = query.limit(options.limit);
  }
  
  if (options.offset) {
    query = query.range(options.offset, options.offset + (options.limit || 10) - 1);
  }
  
  const { data, error } = await query;
  return { data, error };
};

// Organizations helpers
export const createOrganization = async (organization) => {
  const { data, error } = await supabase
    .from('organizations')
    .insert([organization])
    .select();
  
  return { data, error };
};

export const inviteToOrganization = async (organizationId, email, role) => {
  // This would typically involve sending an email with an invitation link
  // For now, we'll just insert a record directly
  const { data, error } = await supabase
    .from('organization_invitations')
    .insert([{
      organization_id: organizationId,
      email,
      role,
      invited_at: new Date().toISOString()
    }])
    .select();
  
  return { data, error };
};

// Realtime subscriptions
export const subscribeToCallUpdates = (userId, callback) => {
  const subscription = supabase
    .channel('call_updates')
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'call_history',
        filter: `user_id=eq.${userId}`
      },
      payload => {
        callback(payload);
      }
    )
    .subscribe();
  
  return subscription;
};

export const subscribeToTranscriptions = (callId, callback) => {
  const subscription = supabase
    .channel('transcription_updates')
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'transcriptions',
        filter: `call_id=eq.${callId}`
      },
      payload => {
        callback(payload);
      }
    )
    .subscribe();
  
  return subscription;
};
