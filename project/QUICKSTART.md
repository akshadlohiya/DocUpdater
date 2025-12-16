# Quick Start Guide

Get the Automatic Technical Document Updater running in 5 minutes.

## Prerequisites

- Node.js 18 or higher
- A Supabase account (free tier is sufficient)

## Step 1: Configure Supabase

The database schema is already set up. You just need to add your credentials:

1. Create a `.env` file in the project root:
   ```
   VITE_SUPABASE_URL=your-supabase-url
   VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
   ```

2. Get these values from your Supabase dashboard:
   - Go to Settings > API
   - Copy the "Project URL" (VITE_SUPABASE_URL)
   - Copy the "anon public" key (VITE_SUPABASE_ANON_KEY)

## Step 2: Install and Run

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at `http://localhost:5173`

## Step 3: Create Your First Admin User

1. Navigate to `http://localhost:5173`
2. Click "Sign up"
3. Enter your details and create an account
4. Go to your Supabase dashboard > Table Editor > user_profiles
5. Find your user and change the role to `admin`

## Step 4: Create Your First Project

1. Log back into the application
2. Click "New Project" on the dashboard
3. Fill in the details:
   - **Name**: My App Documentation
   - **Description**: Documentation for my application
   - **Application Type**: Web Application
   - **Application URL**: https://example.com (or your app URL)
   - **Comparison Tolerance**: 98% (default)
4. Click "Create Project"

## Step 5: Run Your First Comparison

1. Click on your newly created project
2. Click "Start Run"
3. The system will process sample images (this is a simulation)
4. View the results in the Comparisons tab

## What's Next?

### Explore the Features

- **Dashboard**: View overall statistics and recent activity
- **Projects**: Manage multiple documentation projects
- **Comparisons**: Review detected changes side-by-side
- **Audit Logs**: View comprehensive activity logs (admin only)
- **Users**: Manage user roles and permissions (admin only)

### Understanding User Roles

The system has four permission levels:

1. **Viewer** - Read-only access to everything
2. **Reviewer** - Can approve changes but not create projects
3. **Technical Writer** - Can create projects and start runs
4. **Admin** - Full system access including user management

### Testing the Workflow

1. **Create a project** for your documentation
2. **Start a run** to simulate GUI capture and comparison
3. **Review comparisons** in the Comparisons page
4. **Approve changes** that are intentional
5. **Check audit logs** to see all activities

### Customizing for Production

To use this with real applications:

1. **Implement GUI Capture**:
   - Web apps: Integrate Playwright or Puppeteer
   - Desktop apps: Use platform-specific screenshot APIs

2. **Add Image Storage**:
   - Set up Supabase Storage buckets
   - Update edge function to store images
   - Configure CDN for fast access

3. **Implement Real Comparison**:
   - Integrate OpenCV for pixel comparison
   - Add ML models for semantic analysis
   - Connect GPT-4 Vision for AI descriptions

4. **Document Processing**:
   - Add PDF parsing (PyPDF2, pdfplumber)
   - Add DOCX support (python-docx)
   - Implement update logic

## Common Tasks

### Add a New User

As an admin:
1. Ask the user to sign up
2. Go to Users page
3. Find the user and click "Edit Role"
4. Assign appropriate role

### Export Audit Logs

As an admin:
1. Go to Audit Logs
2. Apply any filters you need
3. Click "Export CSV" or "Export JSON"

### Approve Multiple Changes

1. Go to Comparisons
2. Filter by status: "changed"
3. Click on each comparison
4. Review and approve/reject

### Archive a Project

1. Go to Projects
2. Click on the project
3. Click settings (not implemented in UI yet)
4. Change status to "archived"

Or via Supabase dashboard:
- Table Editor > projects
- Find project and set status to "archived"

## Troubleshooting

### Can't connect to database
- Verify `.env` file exists with correct values
- Check Supabase project is active
- Try restarting the dev server

### No projects showing
- Ensure you're logged in
- Check user role allows viewing projects
- Verify projects exist in database

### Run not processing
- Check edge function is deployed
- View logs in Supabase dashboard
- Verify project configuration is valid

### Permission denied errors
- Check your user role in user_profiles table
- Admin actions require admin role
- Review RLS policies if needed

## Support

For more detailed information:
- **Full Documentation**: See README.md
- **API Reference**: See API.md
- **Deployment Guide**: See DEPLOYMENT.md

## Next Steps

1. **Read the full README** to understand all features
2. **Review the API documentation** for integration
3. **Plan your implementation** of real image processing
4. **Deploy to production** using the deployment guide

---

**Congratulations!** You now have a working technical documentation automation system. Start by exploring the interface and understanding the workflow, then customize it for your specific needs.
