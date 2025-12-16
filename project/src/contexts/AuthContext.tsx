import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';
import type { UserRole } from '../lib/database.types';

interface UserProfile {
  id: string;
  email: string;
  role: UserRole;
  full_name: string | null;
  avatar_url: string | null;
}

interface AuthContextType {
  user: User | null;
  profile: UserProfile | null;
  session: Session | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>;
  signUp: (email: string, password: string, fullName: string) => Promise<{ error: Error | null }>;
  signOut: () => Promise<void>;
  hasRole: (roles: UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      if (session?.user) {
        fetchProfile(session.user.id);
      } else {
        setLoading(false);
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      if (session?.user) {
        fetchProfile(session.user.id);
      } else {
        setProfile(null);
        setLoading(false);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const fetchProfile = async (userId: string) => {
    try {
      const { data, error } = await supabase
        .from('user_profiles')
        .select('*')
        .eq('id', userId)
        .maybeSingle();

      if (error) throw error;
      setProfile(data);
    } catch (error) {
      console.error('Error fetching profile:', error);
    } finally {
      setLoading(false);
    }
  };

  const signIn = async (email: string, password: string) => {
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      return { error };
    } catch (error) {
      return { error: error as Error };
    }
  };

  const signUp = async (email: string, password: string, fullName: string) => {
    try {
      const { data: authData, error: authError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
          },
        },
      });

      if (authError) {
        return { error: authError };
      }

      // Explicitly create user profile if user was created
      if (authData.user) {
        // Try RPC function first (most reliable - uses SECURITY DEFINER)
        const { error: rpcError } = await supabase.rpc('create_user_profile', {
          user_id: authData.user.id,
          user_email: email,
          user_full_name: fullName
        });

        if (rpcError) {
          console.warn('RPC function failed, trying direct insert:', rpcError.message);
          
          // Fallback to direct insert
          const { error: directInsertError } = await supabase
            .from('user_profiles')
            .upsert({
              id: authData.user.id,
              email: email,
              full_name: fullName,
              role: 'viewer', // Default role
            }, {
              onConflict: 'id'
            });

          if (directInsertError) {
            console.error('Both RPC and direct insert failed:', directInsertError);
            console.error('Profile error details:', JSON.stringify(directInsertError, null, 2));
            // Don't fail signup - database trigger should handle it
            // But log the error for debugging
          } else {
            console.log('User profile created via direct insert');
          }
        } else {
          console.log('User profile created successfully via RPC function');
        }
      }

      return { error: null };
    } catch (error) {
      console.error('Signup error:', error);
      return { error: error as Error };
    }
  };

  const signOut = async () => {
    await supabase.auth.signOut();
  };

  const hasRole = (roles: UserRole[]) => {
    if (!profile) return false;
    return roles.includes(profile.role);
  };

  const value = {
    user,
    profile,
    session,
    loading,
    signIn,
    signUp,
    signOut,
    hasRole,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
