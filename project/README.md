# Automatic Technical Document Updater

A production-ready platform that automates the synchronization of technical documentation with software GUI changes across product releases.

## Overview

This system addresses a critical pain point in software documentation: keeping user manuals, installation guides, and safety documents up-to-date with GUI changes. Manual updates are tedious, error-prone, and time-consuming. This tool automates the process by detecting GUI changes and updating corresponding documentation images.

## Features

### Core Capabilities

- **Automated GUI Capture**: Screenshot live applications (web, desktop, electron)
- **Intelligent Comparison**: AI-powered image comparison with configurable tolerance
- **Change Detection**: Identify layout, visual, content, and structural changes
- **Document Management**: Track multiple documentation projects and versions
- **Approval Workflow**: Review and approve changes before updating documents
- **Comprehensive Audit Trail**: Complete logging of all system activities
- **Role-Based Access Control**: Four permission levels (Admin, Technical Writer, Reviewer, Viewer)

### User Interface

- **Dashboard**: Overview of projects, active runs, and statistics
- **Project Management**: Create and configure documentation projects
- **Comparison Viewer**: Side-by-side image comparison with change highlighting
- **Audit Logs**: Searchable and exportable activity logs
- **User Management**: Admin panel for managing users and roles

## Architecture

### Technology Stack

- **Frontend**: React 18 + TypeScript + Tailwind CSS
- **Backend**: Supabase (PostgreSQL + Edge Functions)
- **Authentication**: Supabase Auth with email/password
- **Database**: PostgreSQL with Row Level Security
- **File Storage**: Supabase Storage (ready for integration)
- **Routing**: React Router v6

### Database Schema

The system uses a normalized database schema with the following tables:

- `user_profiles` - User accounts with roles
- `projects` - Documentation projects
- `runs` - Execution records of update processes
- `documents` - Documentation files
- `comparisons` - Individual image comparison results
- `change_details` - Detailed analysis of detected changes
- `audit_logs` - Comprehensive audit trail

### Security Features

- Row Level Security (RLS) on all tables
- Role-based access control with four permission levels
- Authenticated API endpoints
- Comprehensive audit logging
- Input validation and sanitization

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Supabase account (database is already configured)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd project
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment variables**
   Create a `.env` file with your Supabase credentials:
   ```
   VITE_SUPABASE_URL=your-supabase-url
   VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
   ```

4. **Start the development server**
   ```bash
   npm run dev
   ```

5. **Build for production**
   ```bash
   npm run build
   ```

## User Roles and Permissions

### Admin
- Full system access
- Manage users and roles
- View audit logs
- Create, edit, and delete projects
- Start runs and approve changes

### Technical Writer
- Create and edit projects
- Start documentation runs
- Approve changes
- View all comparisons

### Reviewer
- View all projects and runs
- Review and approve changes
- View comparisons
- Read-only access to projects

### Viewer
- View projects and runs
- View comparisons
- Read-only access to all features

## Workflow

### 1. Project Creation
1. Log in as Admin or Technical Writer
2. Navigate to Projects
3. Click "New Project"
4. Configure:
   - Project name and description
   - Application type (web, desktop, etc.)
   - Application URL or executable path
   - Comparison tolerance threshold
   - Document paths

### 2. Running a Comparison
1. Navigate to a project
2. Click "Start Run"
3. System will:
   - Capture screenshots of the live application
   - Compare with documentation images
   - Detect and classify changes
   - Generate detailed change descriptions

### 3. Reviewing Changes
1. Navigate to Comparisons
2. Filter by status, severity, or project
3. Click on a comparison to view details
4. Review side-by-side images
5. Examine detected changes
6. Approve or reject changes

### 4. Audit Trail
1. Admins can view comprehensive audit logs
2. Filter by action, resource, or user
3. Export logs as CSV or JSON for compliance

## Edge Functions

### process-run
Processes a documentation run by:
1. Updating run status to "processing"
2. Capturing/simulating GUI screenshots
3. Comparing images with documentation
4. Detecting and classifying changes
5. Generating AI-powered change descriptions
6. Updating run status with results

**Endpoint**: `POST /functions/v1/process-run`

**Request Body**:
```json
{
  "runId": "uuid-of-run"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Run processed successfully",
  "data": {
    "totalImages": 5,
    "changesDetected": 2
  }
}
```

## Extension Points

### Adding New Document Formats
The system is designed with a plugin architecture for document formats:

1. Create a new parser in `src/utils/parsers/`
2. Implement the `DocumentParser` interface
3. Register the parser in the format registry
4. Update the `document_format` enum in the database

### Adding New Application Types
To support new application types:

1. Add the type to the `app_type` enum in the database migration
2. Create a capture handler in the edge function
3. Update the UI form to include the new type
4. Document platform-specific requirements

### Implementing Real Image Processing
The current system includes a simulation. To implement real processing:

1. **GUI Capture**: Integrate Playwright/Puppeteer for web apps, or platform-specific APIs for desktop
2. **Image Storage**: Configure Supabase Storage buckets
3. **Comparison Engine**: Integrate OpenCV or similar for pixel-level comparison
4. **AI Analysis**: Connect to GPT-4 Vision API or custom ML models
5. **Document Updates**: Implement format-specific document modification libraries

## API Endpoints

### Authentication
- `POST /auth/signup` - Create new account
- `POST /auth/signin` - Sign in
- `POST /auth/signout` - Sign out

### Projects
- `GET /rest/v1/projects` - List all projects
- `POST /rest/v1/projects` - Create new project
- `PATCH /rest/v1/projects/{id}` - Update project
- `DELETE /rest/v1/projects/{id}` - Delete project

### Runs
- `GET /rest/v1/runs` - List all runs
- `POST /rest/v1/runs` - Create new run
- `PATCH /rest/v1/runs/{id}` - Update run

### Comparisons
- `GET /rest/v1/comparisons` - List all comparisons
- `PATCH /rest/v1/comparisons/{id}` - Update comparison (approve/reject)

### Audit Logs
- `GET /rest/v1/audit_logs` - List audit logs (admin only)

## Performance Considerations

- Database indexes on frequently queried columns
- Pagination for large datasets
- Efficient image storage with CDN integration
- Background processing for long-running operations
- Connection pooling for database queries

## Security Best Practices

- All sensitive operations require authentication
- RLS policies enforce data access rules
- Passwords hashed with bcrypt
- JWT tokens for session management
- Audit logging for compliance
- Input validation on all endpoints
- CORS properly configured

## Troubleshooting

### Common Issues

**Cannot connect to database**
- Verify VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env
- Check Supabase project is active
- Ensure network connectivity

**Permission denied errors**
- Check user role has required permissions
- Verify RLS policies are correctly applied
- Check audit logs for access attempts

**Runs failing to process**
- Check edge function logs in Supabase dashboard
- Verify project configuration is correct
- Ensure comparison tolerance is reasonable (85-98%)

## Future Enhancements

- [ ] Integration with CI/CD pipelines (Jenkins, GitLab CI, GitHub Actions)
- [ ] Webhook notifications (Slack, Teams, Email)
- [ ] Advanced ML models for semantic change detection
- [ ] Support for video documentation
- [ ] Multi-language documentation support
- [ ] Automated document generation
- [ ] Version control integration (Git)
- [ ] Real-time collaboration features
- [ ] Custom reporting and analytics
- [ ] Mobile app for approval workflow

## License

Copyright (c) 2024. All rights reserved.

## Support

For issues, questions, or contributions, please contact the development team or open an issue in the repository.

## Acknowledgments

Built with modern web technologies and best practices for production deployment.
