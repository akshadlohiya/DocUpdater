-- Run this SQL in your Supabase SQL Editor to fix user profile creation
-- This will ensure profiles are created when users sign up

-- Step 1: Fix the trigger function to handle errors better
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
    RAISE WARNING 'Error creating user profile for user %: %', new.id, SQLERRM;
    RETURN new;
END;
$$ LANGUAGE plpgsql;

-- Step 2: Ensure the trigger exists
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW 
  EXECUTE FUNCTION public.handle_new_user();

-- Step 3: Fix RLS policies to allow profile creation
-- Drop existing insert policy
DROP POLICY IF EXISTS "System can insert profiles" ON user_profiles;

-- Create a policy that allows authenticated users to insert their own profile
CREATE POLICY "Users can insert own profile"
  ON user_profiles FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = id);

-- Also allow the trigger function (service role) to insert
-- Note: SECURITY DEFINER should handle this, but this is a backup
DROP POLICY IF EXISTS "Service role can insert profiles" ON user_profiles;
CREATE POLICY "Service role can insert profiles"
  ON user_profiles FOR INSERT
  TO service_role
  WITH CHECK (true);

-- Step 4: Verify the trigger is working
-- You can test by checking if the trigger function exists:
SELECT 
  trigger_name, 
  event_manipulation, 
  event_object_table, 
  action_statement
FROM information_schema.triggers
WHERE trigger_name = 'on_auth_user_created';

-- Step 5: For existing users without profiles, you can manually create them:
-- (Only run this if you have users in auth.users but not in user_profiles)
-- INSERT INTO public.user_profiles (id, email, role, full_name)
-- SELECT 
--   id,
--   email,
--   'viewer',
--   raw_user_meta_data->>'full_name' as full_name
-- FROM auth.users
-- WHERE id NOT IN (SELECT id FROM public.user_profiles)
-- ON CONFLICT (id) DO NOTHING;

