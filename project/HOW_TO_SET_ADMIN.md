# How to Set Your Role to Admin in Supabase

## Quick Steps

### 1. Go to Supabase Dashboard
Open your browser and go to: **https://supabase.com/dashboard**

Login if needed.

### 2. Select Your Project
Click on your project that matches: `vxpljpbunuqzvsdrhodq.supabase.co`

### 3. Open Table Editor
Look at the **left sidebar** and click on **"Table Editor"** (looks like a grid/table icon)

### 4. Find the Profiles Table
In the list of tables, click on **`profiles`**

### 5. Find Your User
Look for the row where the **email** column shows `abc@gmail.com`

### 6. Change the Role
1. Find the **`role`** column in that row
2. **Double-click** on the cell (it currently says `user`)
3. **Type**: `admin`
4. Press **Enter** to save

### 7. Restart Your Server
```bash
cd c:\Users\revor\Downloads\project\project
python server.py
```

### 8. Test It
1. Clear your browser cache (or use incognito mode)
2. Go to: http://localhost:8001/auth
3. Login with abc@gmail.com
4. You should now see **"ADMIN"** badge (yellow) and the **"Generate"** tab

---

## Visual Guide

![Supabase Table Editor Guide](supabase_role_guide.png)

The image above shows where to click and what to change.

---

## Troubleshooting

**Don't see the profiles table?**
- Make sure you selected the correct project
- The table should exist if you've signed up at least once

**Can't edit the role?**
- Make sure you're logged in as the project owner
- You need admin access to the Supabase project itself

**Still showing as USER after changing?**
- Make sure you pressed Enter to save
- Restart the server
- Clear browser cache completely
- Try logging out and back in
