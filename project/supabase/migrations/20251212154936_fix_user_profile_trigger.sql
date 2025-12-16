-- Fix user profile creation trigger and RLS policies
-- This migration ensures user profiles are created on signup

-- First, ensure the trigger function exists and can bypass RLS
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger 
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.user_profiles (id, email, role, full_name)
  VALUES (
    new.id,
    COALESCE(new.email, new.raw_user_meta_data->>'email'),
    'viewer',
    COALESCE(new.raw_user_meta_data->>'full_name', '')
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN new;
EXCEPTION
  WHEN others THEN
    -- Log error but don't fail the trigger
    RAISE WARNING 'Error creating user profile: %', SQLERRM;
    RETURN new;
END;
$$ LANGUAGE plpgsql;

-- Ensure the trigger exists
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW 
  EXECUTE FUNCTION public.handle_new_user();

-- Add a policy that allows service role to insert (for the trigger)
-- This is a backup in case SECURITY DEFINER doesn't work as expected
DROP POLICY IF EXISTS "Service role can insert profiles" ON user_profiles;
CREATE POLICY "Service role can insert profiles"
  ON user_profiles FOR INSERT
  TO service_role
  WITH CHECK (true);

-- Also ensure authenticated users can insert their own profile during signup
-- This helps if the trigger fails and we need client-side fallback
DROP POLICY IF EXISTS "System can insert profiles" ON user_profiles;
CREATE POLICY "System can insert profiles"
  ON user_profiles FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = id);

-- Add a policy for anon users to insert their own profile (for immediate signup)
-- This is needed if email confirmation is disabled
DROP POLICY IF EXISTS "Anon can insert own profile on signup" ON user_profiles;
CREATE POLICY "Anon can insert own profile on signup"
  ON user_profiles FOR INSERT
  TO anon
  WITH CHECK (true);

