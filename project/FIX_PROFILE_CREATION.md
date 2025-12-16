# Fix: User Profiles Not Being Created on Signup

## Problem
When users sign up, their profile is not being created in the `user_profiles` table.

## Solution

### Step 1: Run SQL Script in Supabase

**IMPORTANT:** You must run the SQL script in your Supabase dashboard to set up the database trigger and RPC function.

1. Go to your Supabase Dashboard: https://supabase.com/dashboard
2. Select your project: `iyvlqbdoovzvcdcuucqo`
3. Go to **SQL Editor** (left sidebar)
4. Click **New Query**
5. Copy and paste the **entire contents** of `setup_user_profiles.sql`
6. Click **Run** (or press Ctrl+Enter)

This will:
- Create/update the database trigger that automatically creates profiles
- Create an RPC function for client-side profile creation
- Fix RLS policies to allow profile creation

### Step 2: Verify the Setup

After running the SQL, verify the trigger exists by running this query:

```sql
SELECT 
  trigger_name, 
  event_manipulation, 
  event_object_table, 
  action_statement
FROM information_schema.triggers
WHERE trigger_name = 'on_auth_user_created';
```

You should see one row with the trigger details.

### Step 3: Test Signup

1. Go to your application's signup page
2. Create a new user account
3. Check the `user_profiles` table in Supabase:
   - Go to **Table Editor** > `user_profiles`
   - You should see the new user's profile

### Step 4: (Optional) Create Profiles for Existing Users

If you have users in `auth.users` but not in `user_profiles`, run this in the SQL Editor:

```sql
INSERT INTO public.user_profiles (id, email, role, full_name)
SELECT 
  id,
  COALESCE(email, ''),
  'viewer',
  COALESCE(raw_user_meta_data->>'full_name', '') as full_name
FROM auth.users
WHERE id NOT IN (SELECT id FROM public.user_profiles)
ON CONFLICT (id) DO NOTHING;
```

## How It Works

The fix uses a **three-layer approach**:

1. **Database Trigger** (Primary): Automatically creates a profile when a user is inserted into `auth.users`
2. **RPC Function** (Fallback 1): Client code calls `create_user_profile()` RPC function which uses `SECURITY DEFINER` to bypass RLS
3. **Direct Insert** (Fallback 2): Client code directly inserts into `user_profiles` table

The code tries methods in order until one succeeds.

## Troubleshooting

### Check if Trigger is Firing

1. Go to **Database** > **Functions** in Supabase
2. Find `handle_new_user` function
3. Check the logs for any errors

### Check RLS Policies

Run this query to see all policies on `user_profiles`:

```sql
SELECT 
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual,
  with_check
FROM pg_policies
WHERE tablename = 'user_profiles';
```

### Check Browser Console

Open browser DevTools (F12) and check the Console tab when signing up. You should see:
- "User profile created successfully via RPC function" (if RPC works)
- "User profile created via direct insert" (if direct insert works)
- Error messages if both fail

### Common Issues

1. **Trigger not running**: Make sure you ran the SQL script in Step 1
2. **RLS blocking**: The SQL script fixes RLS policies, but make sure it ran successfully
3. **Email confirmation required**: If email confirmation is enabled, users need to confirm before they can sign in, but the profile should still be created

## Next Steps

After running the SQL script, try signing up a new user. The profile should be created automatically.

