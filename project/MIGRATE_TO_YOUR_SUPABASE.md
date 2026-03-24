# How to Switch to Your Own Supabase Project

## Step 1: Create a New Supabase Project (or use existing)

### Option A: Create New Project
1. Go to https://supabase.com/dashboard
2. Click **"New Project"**
3. Fill in:
   - **Name**: Documentation System (or whatever you want)
   - **Database Password**: Choose a strong password (save it!)
   - **Region**: Choose closest to you
4. Click **"Create new project"**
5. Wait 2-3 minutes for setup to complete

### Option B: Use Existing Project
If you already have a Supabase project, just use that one.

---

## Step 2: Get Your Supabase Credentials

Once your project is ready:

1. Go to **Settings** (⚙️ icon in left sidebar)
2. Click on **API**
3. You'll see:

   **Project URL:**
   ```
   https://xxxxxxxxxxxxx.supabase.co
   ```
   Copy this!

   **Project API keys:**
   - **anon/public key** - Copy this (it's safe for frontend)
   - **service_role key** - DON'T need this anymore

   **JWT Secret:**
   - Scroll down to JWT Settings
   - Copy the JWT Secret

---

## Step 3: Run the Database Migration

Your project already has the migration file. You need to run it on YOUR Supabase project.

### Method 1: Using Supabase SQL Editor (Easiest)

1. In Supabase dashboard, click **SQL Editor** in left sidebar
2. Click **"New query"**
3. Copy the contents of this file:
   `c:\Users\revor\Downloads\project\project\supabase\migrations\20260202163400_create_users_with_roles.sql`
4. Paste it into the SQL Editor
5. Click **"Run"** or press Ctrl+Enter
6. You should see "Success" ✅

### Method 2: Using Supabase CLI (Advanced)
```bash
# Install Supabase CLI first
npm install -g supabase

# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref YOUR_PROJECT_ID

# Run migrations
supabase db push
```

---

## Step 4: Update Backend .env File

Open: `c:\Users\revor\Downloads\project\project\.env`

Replace with YOUR credentials:

```env
VITE_SUPABASE_URL=https://YOUR-PROJECT-ID.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.YOUR-ANON-KEY-HERE
# Get this from your Supabase project settings -> API -> JWT Secret
SUPABASE_JWT_SECRET=your-actual-jwt-secret-from-your-project
```

---

## Step 5: Update Frontend .env File

Open: `c:\Users\revor\Downloads\project\project\project2\.env`

Replace with YOUR credentials:

```env
VITE_SUPABASE_URL=https://YOUR-PROJECT-ID.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.YOUR-ANON-KEY-HERE
```

---

## Step 6: Test the Setup

1. **Restart your server:**
   ```bash
   cd c:\Users\revor\Downloads\project\project
   python server.py
   ```

2. **Rebuild the frontend (if needed):**
   ```bash
   cd c:\Users\revor\Downloads\project\project\project2
   npm run build
   ```

3. **Test signup:**
   - Go to http://localhost:8001/auth
   - Click "Sign Up"
   - Create a new account with YOUR email
   - Check Supabase → Authentication → Users (you should see your user)
   - Check Supabase → Table Editor → profiles (you should see your profile with role "user")

4. **Promote yourself to admin:**
   - Go to Supabase → Table Editor → profiles
   - Find your email
   - Double-click the "role" cell
   - Change from "user" to "admin"
   - Press Enter

5. **Test admin access:**
   - Clear browser cache
   - Login again
   - You should see "ADMIN" badge and "Generate" tab ✅

---

## Quick Checklist

- [ ] Created/selected your Supabase project
- [ ] Copied Project URL
- [ ] Copied anon/public key
- [ ] Copied JWT Secret
- [ ] Ran the migration SQL (created profiles table)
- [ ] Updated backend `.env` file
- [ ] Updated frontend `.env` file in project2 folder
- [ ] Restarted server
- [ ] Signed up with your email
- [ ] Promoted your account to admin in profiles table
- [ ] Tested and saw ADMIN badge

---

## Troubleshooting

**"relation profiles does not exist"**
- You forgot to run the migration SQL
- Go to SQL Editor and paste/run the migration file

**"Invalid JWT"**
- Wrong JWT Secret in .env
- Make sure you copied the JWT Secret from YOUR project, not the old one

**"User already exists"**
- That email was used in the old Supabase
- Use a different email, or delete the user from the old project

**Frontend shows old Supabase**
- Check `project2/.env` has YOUR credentials
- Rebuild frontend: `npm run build`
- Clear browser cache

---

## Files to Update

| File | What to Change |
|------|----------------|
| `project/.env` | All 3 Supabase values |
| `project/project2/.env` | SUPABASE_URL and ANON_KEY |

That's it! Your project will now use YOUR Supabase instead of someone else's.
