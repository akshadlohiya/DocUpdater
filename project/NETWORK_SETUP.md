# Network Access Setup Guide

## Overview
The documentation server can now be accessed from multiple PCs on your local network with role-based permissions:
- **Admin users**: Can generate documentation and compare PDFs
- **Regular users**: Can view and download PDFs from the library

## Initial Setup

### 1. Install Dependencies
```bash
cd c:\Users\revor\Downloads\project\project
pip install PyJWT python-dotenv
```

### 2. Configure Supabase JWT Secret

1. Go to your Supabase project: https://vxpljpbunuqzvsdrhodq.supabase.co
2. Navigate to: **Project Settings** → **API** → **JWT Settings**
3. Copy the **JWT Secret** (not the anon key!)
4. Update `.env` file and replace `your-supabase-jwt-secret-here` with your actual JWT secret

### 3. Create Admin Account

Admin accounts must be manually created for security. After a user signs up:

1. Go to your Supabase project dashboard
2. Navigate to: **Table Editor** → **profiles**
3. Find the user you want to make admin
4. Edit their row and change `role` from `user` to `admin`
5. Save the changes

## Starting the Server

### On the Server PC (where server.py runs):

```bash
cd c:\Users\revor\Downloads\project\project
python server.py
```

The server will start on `0.0.0.0:8001` (accessible from network).

### Find Your Server IP Address

On Windows (Command Prompt or PowerShell):
```bash
ipconfig
```

Look for **IPv4 Address** under your active network adapter (usually Wi-Fi or Ethernet).
Example: `192.168.1.100`

## Accessing from Other PCs

### On Client PCs (same network):

1. Open a web browser
2. Navigate to: `http://<SERVER-IP>:8001/auth`
   - Replace `<SERVER-IP>` with the actual IP from above
   - Example: `http://192.168.1.100:8001/auth`

3. Sign in with your credentials
   - Admin users will see: Generate tab + Library tab
   - Regular users will see: Library tab only

## Network Access URLs

| Purpose | URL Format | Example |
|---------|-----------|---------|
| Authentication/Login | `http://<SERVER-IP>:8001/auth` | `http://192.168.1.100:8001/auth` |
| Main App (old) | `http://<SERVER-IP>:8001/` | `http://192.168.1.100:8001/` |

## User Roles and Permissions

### Admin Role
- ✅ Generate documentation for applications
- ✅ Compare PDF versions
- ✅ View and download from library
- ✅ Full system access

### User Role
- ❌ Cannot generate documentation
- ❌ Cannot compare PDFs
- ✅ View library
- ✅ Download PDFs from library

## Troubleshooting

### Cannot Connect from Other PC

1. **Check Firewall**: Ensure Windows Firewall allows port 8001
   ```powershell
   # Run as Administrator
   New-NetFirewallRule -DisplayName "Documentation Server" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow
   ```

2. **Verify Server is Running**: On server PC, check if server.py is active

3. **Check Network**: Ensure both PCs are on the same network (same WiFi or LAN)

4. **Ping Test**: From client PC, ping the server
   ```bash
   ping <SERVER-IP>
   ```

### Authentication Errors

1. **"Authentication required"**: Make sure you're logged in
2. **"Token has expired"**: Sign out and sign in again
3. **"Admin access required"**: Your account needs admin role (see setup above)

### JWT Secret Issues

If you get JWT validation errors:
1. Double-check the `SUPABASE_JWT_SECRET` in `.env`
2. Make sure there are no extra spaces
3. Restart the server after updating `.env`

## Security Notes

⚠️ **Important Security Considerations:**

1. **Local Network Only**: This setup is designed for local/trusted networks
2. **No HTTPS**: Traffic is not encrypted. Don't use on public networks.
3. **Firewall**: Only allow port 8001 from trusted IPs if possible
4. **Admin Accounts**: Keep admin credentials secure
5. **Production Use**: For internet-facing deployment, add HTTPS and additional security

## Example Workflow

### Admin Workflow:
1. Sign in at `http://192.168.1.100:8001/auth`
2. Navigate to **Generate** tab
3. Configure and generate documentation for an app
4. Switch to **Library** tab to verify it appears
5. Download the PDF if needed

### User Workflow:
1. Sign in at `http://192.168.1.100:8001/auth`
2. View available documentation in **Library** tab
3. Click **Download PDF** button to get the file
4. PDF downloads to their PC's Downloads folder

## Quick Reference Commands

```bash
# Start server
python server.py

# Check server IP
ipconfig

# Install dependencies
pip install -r requirements.txt

# Allow firewall (Run as Admin)
New-NetFirewallRule -DisplayName "Documentation Server" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow
```
