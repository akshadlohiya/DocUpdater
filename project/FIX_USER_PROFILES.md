# Fix: User Profiles Not Being Created on Signup

## Problem
When users sign up, their profile is not being created in the `user_profiles` table.

## Root Cause
The database trigger that automatically creates user profiles might not be set up correctly in your Supabase instance, or the RLS policies are blocking the insert.

## Solution

### Step 1: Run the SQL Script in Supabase

1. Go to your Supabase Dashboard: https://supabase.com/dashboard
2. Select your project: `iyvlqbdoovzvcdcuucqo`
3. Go to **SQL Editor** (left sidebar)
4. Click **New Query**
5. Copy and paste the contents of `fix_user_profiles.sql` (or see below)
6. Click **Run** (or press Ctrl+Enter)

**SQL Script:**
```sql
-- Fix the trigger function
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
    RAISE WARNING 'Error creating user profile for user %: %', new.id, SQLERRM;
    RETURN new;
END;
$$ LANGUAGE plpgsql;

-- Ensure the trigger exists
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW 
  EXECUTE FUNCTION public.handle_new_user();

-- Fix RLS policies
DROP POLICY IF EXISTS "System can insert profiles" ON user_profiles;
CREATE POLICY "Users can insert own profile"
  ON user_profiles FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Service role can insert profiles" ON user_profiles;
CREATE POLICY "Service role can insert profiles"
  ON user_profiles FOR INSERT
  TO service_role
  WITH CHECK (true);
```

### Step 2: (Optional) Create RPC Function as Fallback

Run this in the SQL Editor as well:

```sql
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
    user_full_name
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

GRANT EXECUTE ON FUNCTION public.create_user_profile(uuid, text, text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.create_user_profile(uuid, text, text) TO anon;
```

### Step 3: Verify the Trigger

Run this query to verify the trigger exists:

```sql
SELECT 
  trigger_name, 
  event_manipulation, 
  event_object_table, 
  action_statement
FROM information_schema.triggers
WHERE trigger_name = 'on_auth_user_created';
```

You should see a row with the trigger details.

### Step 4: Test Signup

1. Go to your application's signup page
2. Create a new user account
3. Check the `user_profiles` table in Supabase:
   - Go to **Table Editor** > `user_profiles`
   - You should see the new user's profile

### Step 5: (Optional) Create Profiles for Existing Users

If you have users in `auth.users` but not in `user_profiles`, run this:

```sql
INSERT INTO public.user_profiles (id, email, role, full_name)
SELECT 
  id,
  email,
  'viewer',
  COALESCE(raw_user_meta_data->>'full_name', '') as full_name
FROM auth.users
WHERE id NOT IN (SELECT id FROM public.user_profiles)
ON CONFLICT (id) DO NOTHING;
```

## Troubleshooting

### Check if Trigger is Firing

1. Go to **Database** > **Functions** in Supabase
2. Find `handle_new_user`
3. Check the logs for any errors

### Check RLS Policies

1. Go to **Authentication** > **Policies** in Supabase
2. Verify the policies for `user_profiles` table
3. Make sure the insert policy allows authenticated users

### Check Email Confirmation Settings

1. Go to **Authentication** > **Providers** > **Email**
2. If "Confirm email" is enabled, users need to confirm their email before they can sign in
3. The trigger should still create the profile even if email confirmation is required

### Debug in Browser Console

1. Open browser DevTools (F12)
2. Go to Console tab
3. Try signing up a new user
4. Look for any error messages related to profile creation

## What Changed in the Code

The `signUp` function in `AuthContext.tsx` now:
1. Waits 500ms for the database trigger to run
2. Tries to create the profile directly
3. Falls back to RPC function if direct insert fails
4. Logs errors but doesn't fail signup (trigger should handle it)

## Still Not Working?

If profiles are still not being created:

1. Check Supabase logs: **Logs** > **Postgres Logs**
2. Verify the trigger function exists and is correct
3. Check if there are any RLS policy conflicts
4. Make sure the `user_profiles` table exists and has the correct schema
5. Try disabling email confirmation temporarily to test

