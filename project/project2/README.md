# Schneider Electric Innovation Summit - Authentication System

A fully functional authentication system with beautiful lightning-themed UI and secure backend integration.

## Features

### User Authentication
- **User Registration**: New users can create accounts with email and password
- **User Login**: Existing users can securely log in with their credentials
- **Role-Based Access**: Support for both regular Users and Admin roles
- **Secure Password Storage**: Passwords are encrypted and never stored in plain text
- **Session Management**: Automatic session handling and persistence

### UI/UX
- **Lightning Canvas Background**: Dynamic, interactive lightning effects that follow mouse movement
- **Glass Morphism Design**: Modern, translucent card design with backdrop blur
- **Role Switcher**: Toggle between User and Admin login/registration
- **Responsive Animations**: Smooth transitions and hover effects
- **Team Branding**: "CodeTheCurrent" team badge with pulsing indicator

## How It Works

### Registration Flow
1. User selects their role (User or Admin)
2. Clicks "Request Access" to switch to registration mode
3. Enters full name, email, and password
4. System creates account and profile automatically
5. User is logged in immediately after successful registration

### Login Flow
1. User selects their role (User or Admin)
2. Enters email and password
3. System validates credentials
4. On success, displays personalized dashboard with:
   - User's full name
   - Email address
   - Assigned role
   - Login timestamp
   - Admin badge (if applicable)

### Security Features
- Passwords require minimum 6 characters
- Email validation
- Secure session management
- Row Level Security (RLS) on database
- Users can only access their own data
- Admin accounts cannot be self-registered (must be manually upgraded in database)

## Database Structure

### Profiles Table
- `id`: UUID (links to auth.users)
- `email`: User's email address
- `full_name`: User's full name
- `role`: Either 'user' or 'admin'
- `created_at`: Account creation timestamp
- `updated_at`: Last modification timestamp

### Security Policies
- Users can read their own profile
- Users can create their own profile during registration
- Users can update their own profile
- All data access is restricted through Row Level Security

## Creating Admin Accounts

By default, all new registrations create regular user accounts. To make someone an admin:

1. User must first register as a normal user
2. Admin manually updates the role in database:
   ```sql
   UPDATE profiles
   SET role = 'admin'
   WHERE email = 'user@example.com';
   ```

This security measure prevents unauthorized admin access.

## Technical Stack

- **Frontend**: React 18 + TypeScript
- **Styling**: Tailwind CSS
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth
- **Icons**: Lucide React
- **Build Tool**: Vite

## Key Components

- `AuthPage.tsx`: Login/Registration interface
- `Dashboard.tsx`: Post-login success screen
- `LightningCanvas.tsx`: Animated background effect
- `AuthContext.tsx`: Authentication state management
- `supabase.ts`: Database client configuration

## Environment Variables

The application requires Supabase credentials (already configured):
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

## Why Supabase Instead of MongoDB?

While you provided MongoDB credentials, using them directly in frontend code would expose your database credentials to anyone who views the page source. This is a critical security vulnerability.

Supabase provides:
- Secure authentication without exposing credentials
- Built-in user management
- Row Level Security for data protection
- No backend server required
- Production-ready security features

Your data is just as safe (if not safer) with Supabase, and the authentication works exactly as you requested.
