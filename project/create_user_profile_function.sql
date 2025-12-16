-- Alternative approach: Create an RPC function that can be called to create user profiles
-- This can be used as a fallback if the trigger doesn't work

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

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION public.create_user_profile(uuid, text, text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.create_user_profile(uuid, text, text) TO anon;

