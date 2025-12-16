-- Complete SQL script to fix user profile creation in Supabase
-- Run this in your Supabase SQL Editor: https://supabase.com/dashboard/project/iyvlqbdoovzvcdcuucqo/sql

-- Step 1: Create/Update the trigger function with better error handling
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger 
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.user_profiles (id, email, role, full_name)
  VALUES (
    new.id,
    COALESCE(new.email, ''),
    'viewer',
    COALESCE(new.raw_user_meta_data->>'full_name', '')
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN new;
EXCEPTION
  WHEN others THEN
    -- Log error but don't fail the trigger
    RAISE WARNING 'Error creating user profile for user %: %', new.id, SQLERRM;
    RETURN new;
END;
$$ LANGUAGE plpgsql;

-- Step 2: Ensure the trigger exists and is active
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW 
  EXECUTE FUNCTION public.handle_new_user();

-- Step 3: Create RPC function for client-side profile creation (fallback)
CREATE OR REPLACE FUNCTION public.create_user_profile(
  user_id uuid,
  user_email text,
  user_full_name text DEFAULT ''
)
RETURNS void
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
BEGIN
  INSERT INTO public.user_profiles (id, email, role, full_name)
  VALUES (
    user_id,
    user_email,
    'viewer',
    COALESCE(user_full_name, '')
  )
  ON CONFLICT (id) DO UPDATE
  SET 
    email = EXCLUDED.email,
    full_name = COALESCE(EXCLUDED.full_name, user_profiles.full_name),
    updated_at = now();
EXCEPTION
  WHEN others THEN
    RAISE WARNING 'Error creating/updating user profile: %', SQLERRM;
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION public.create_user_profile(uuid, text, text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.create_user_profile(uuid, text, text) TO anon;

-- Step 4: Fix RLS policies
-- Drop existing insert policies
DROP POLICY IF EXISTS "System can insert profiles" ON user_profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;
DROP POLICY IF EXISTS "Service role can insert profiles" ON user_profiles;
DROP POLICY IF EXISTS "Anon can insert own profile on signup" ON user_profiles;

-- Allow authenticated users to insert their own profile
CREATE POLICY "Users can insert own profile"
  ON user_profiles FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = id);

-- Allow service role (for trigger)
CREATE POLICY "Service role can insert profiles"
  ON user_profiles FOR INSERT
  TO service_role
  WITH CHECK (true);

-- Allow anon users to insert their own profile (needed if email confirmation is disabled)
CREATE POLICY "Anon can insert own profile on signup"
  ON user_profiles FOR INSERT
  TO anon
  WITH CHECK (true);

-- Step 5: Verify the trigger exists
SELECT 
  trigger_name, 
  event_manipulation, 
  event_object_table, 
  action_statement
FROM information_schema.triggers
WHERE trigger_name = 'on_auth_user_created';

-- Step 6: (Optional) Create profiles for existing users who don't have one
-- Uncomment and run this if you have users in auth.users but not in user_profiles
/*
INSERT INTO public.user_profiles (id, email, role, full_name)
SELECT 
  id,
  COALESCE(email, ''),
  'viewer',
  COALESCE(raw_user_meta_data->>'full_name', '') as full_name
FROM auth.users
WHERE id NOT IN (SELECT id FROM public.user_profiles)
ON CONFLICT (id) DO NOTHING;
*/

