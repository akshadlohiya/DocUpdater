# API Documentation

## Overview

The Automatic Technical Document Updater provides a RESTful API through Supabase and custom Edge Functions.

## Authentication

All API endpoints (except signup/signin) require authentication using JWT tokens.

### Headers
```
Authorization: Bearer <jwt-token>
apikey: <supabase-anon-key>
Content-Type: application/json
```

## Base URLs

- **Supabase REST API**: `https://[project-ref].supabase.co/rest/v1/`
- **Edge Functions**: `https://[project-ref].supabase.co/functions/v1/`

---

## Authentication Endpoints

### Sign Up
Create a new user account.

**Endpoint**: `POST /auth/v1/signup`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "options": {
    "data": {
      "full_name": "John Doe"
    }
  }
}
```

**Response** (200 OK):
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "session": {
    "access_token": "jwt-token",
    "refresh_token": "refresh-token"
  }
}
```

### Sign In
Authenticate an existing user.

**Endpoint**: `POST /auth/v1/token?grant_type=password`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response** (200 OK):
```json
{
  "access_token": "jwt-token",
  "refresh_token": "refresh-token",
  "user": {
    "id": "uuid",
    "email": "user@example.com"
  }
}
```

### Sign Out
Sign out the current user.

**Endpoint**: `POST /auth/v1/logout`

**Headers**: Requires Authorization

**Response** (204 No Content)

---

## Projects

### List Projects
Get all projects the user has access to.

**Endpoint**: `GET /rest/v1/projects`

**Query Parameters**:
- `select` - Columns to return (default: `*`)
- `order` - Sort order (e.g., `created_at.desc`)
- `limit` - Number of results (default: unlimited)

**Response** (200 OK):
```json
[
  {
    "id": "uuid",
    "name": "My Application Docs",
    "description": "Documentation for my app",
    "app_type": "web",
    "app_url": "https://example.com",
    "comparison_tolerance": 98.0,
    "status": "active",
    "created_by": "uuid",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### Get Project
Get a specific project by ID.

**Endpoint**: `GET /rest/v1/projects?id=eq.{uuid}`

**Response** (200 OK):
```json
{
  "id": "uuid",
  "name": "My Application Docs",
  "description": "Documentation for my app",
  "app_type": "web",
  "app_url": "https://example.com",
  "comparison_tolerance": 98.0,
  "status": "active",
  "created_by": "uuid",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Create Project
Create a new documentation project.

**Endpoint**: `POST /rest/v1/projects`

**Required Roles**: `admin`, `technical_writer`

**Request Body**:
```json
{
  "name": "My Application Docs",
  "description": "Documentation for my app",
  "app_type": "web",
  "app_url": "https://example.com",
  "comparison_tolerance": 98.0,
  "status": "draft"
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "name": "My Application Docs",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Update Project
Update an existing project.

**Endpoint**: `PATCH /rest/v1/projects?id=eq.{uuid}`

**Required Roles**: `admin`, `technical_writer` (owner)

**Request Body** (partial update):
```json
{
  "name": "Updated Name",
  "comparison_tolerance": 95.0
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "name": "Updated Name",
  "updated_at": "2024-01-01T01:00:00Z"
}
```

### Delete Project
Delete a project and all associated data.

**Endpoint**: `DELETE /rest/v1/projects?id=eq.{uuid}`

**Required Roles**: `admin`

**Response** (204 No Content)

---

## Runs

### List Runs
Get all runs the user has access to.

**Endpoint**: `GET /rest/v1/runs`

**Query Parameters**:
- `project_id` - Filter by project (e.g., `project_id=eq.{uuid}`)
- `status` - Filter by status (e.g., `status=eq.completed`)
- `order` - Sort order (default: `started_at.desc`)

**Response** (200 OK):
```json
[
  {
    "id": "uuid",
    "project_id": "uuid",
    "status": "completed",
    "triggered_by": "uuid",
    "trigger_type": "manual",
    "started_at": "2024-01-01T10:00:00Z",
    "completed_at": "2024-01-01T10:05:00Z",
    "total_images": 50,
    "changes_detected": 5,
    "error_message": null
  }
]
```

### Create Run
Start a new documentation update run.

**Endpoint**: `POST /rest/v1/runs`

**Required Roles**: `admin`, `technical_writer`

**Request Body**:
```json
{
  "project_id": "uuid",
  "status": "pending",
  "trigger_type": "manual",
  "config_snapshot": {
    "tolerance": 98.0
  }
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "status": "pending",
  "started_at": "2024-01-01T10:00:00Z"
}
```

### Get Run Details
Get detailed information about a run.

**Endpoint**: `GET /rest/v1/runs?id=eq.{uuid}&select=*,projects(*)`

**Response** (200 OK):
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "status": "completed",
  "started_at": "2024-01-01T10:00:00Z",
  "completed_at": "2024-01-01T10:05:00Z",
  "total_images": 50,
  "changes_detected": 5,
  "projects": {
    "name": "My Application Docs"
  }
}
```

---

## Comparisons

### List Comparisons
Get all image comparisons.

**Endpoint**: `GET /rest/v1/comparisons`

**Query Parameters**:
- `run_id` - Filter by run (e.g., `run_id=eq.{uuid}`)
- `status` - Filter by status (e.g., `status=eq.changed`)
- `change_severity` - Filter by severity (e.g., `change_severity=eq.major`)

**Response** (200 OK):
```json
[
  {
    "id": "uuid",
    "run_id": "uuid",
    "doc_image_path": "docs/screenshots/login.png",
    "live_image_path": "live/screenshots/login.png",
    "similarity_score": 92.5,
    "status": "changed",
    "change_severity": "minor",
    "is_approved": false,
    "processed_at": "2024-01-01T10:01:00Z"
  }
]
```

### Get Comparison Details
Get detailed information about a comparison including change details.

**Endpoint**: `GET /rest/v1/comparisons?id=eq.{uuid}&select=*,change_details(*)`

**Response** (200 OK):
```json
{
  "id": "uuid",
  "run_id": "uuid",
  "doc_image_path": "docs/screenshots/login.png",
  "similarity_score": 92.5,
  "status": "changed",
  "change_details": [
    {
      "id": "uuid",
      "change_type": "visual",
      "description": "Button color changed from blue to green",
      "severity": "minor",
      "position_x": 100,
      "position_y": 200
    }
  ]
}
```

### Approve/Reject Comparison
Update the approval status of a comparison.

**Endpoint**: `PATCH /rest/v1/comparisons?id=eq.{uuid}`

**Required Roles**: `admin`, `technical_writer`, `reviewer`

**Request Body**:
```json
{
  "is_approved": true,
  "approved_at": "2024-01-01T11:00:00Z"
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "is_approved": true,
  "approved_at": "2024-01-01T11:00:00Z"
}
```

---

## Change Details

### List Changes for Comparison
Get all detected changes for a specific comparison.

**Endpoint**: `GET /rest/v1/change_details?comparison_id=eq.{uuid}`

**Response** (200 OK):
```json
[
  {
    "id": "uuid",
    "comparison_id": "uuid",
    "change_type": "visual",
    "description": "Button color changed from blue to green",
    "position_x": 100,
    "position_y": 200,
    "width": 120,
    "height": 40,
    "severity": "minor",
    "ai_analysis": {
      "confidence": 0.95,
      "recommendation": "Review and approve if intentional"
    },
    "created_at": "2024-01-01T10:01:00Z"
  }
]
```

---

## Audit Logs

### List Audit Logs
Get audit logs (admin only).

**Endpoint**: `GET /rest/v1/audit_logs`

**Required Roles**: `admin`

**Query Parameters**:
- `action` - Filter by action (e.g., `action=eq.create`)
- `resource_type` - Filter by resource (e.g., `resource_type=eq.project`)
- `user_id` - Filter by user (e.g., `user_id=eq.{uuid}`)
- `order` - Sort order (default: `created_at.desc`)
- `limit` - Number of results

**Response** (200 OK):
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "action": "create",
    "resource_type": "project",
    "resource_id": "uuid",
    "details": {
      "name": "New Project"
    },
    "ip_address": "192.168.1.1",
    "created_at": "2024-01-01T10:00:00Z"
  }
]
```

---

## User Profiles

### Get Current User Profile
Get the profile of the authenticated user.

**Endpoint**: `GET /rest/v1/user_profiles?id=eq.{user_id}`

**Response** (200 OK):
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "role": "technical_writer",
  "full_name": "John Doe",
  "avatar_url": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Update User Role
Update a user's role (admin only).

**Endpoint**: `PATCH /rest/v1/user_profiles?id=eq.{uuid}`

**Required Roles**: `admin`

**Request Body**:
```json
{
  "role": "reviewer"
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "role": "reviewer",
  "updated_at": "2024-01-01T11:00:00Z"
}
```

---

## Edge Functions

### Process Run
Process a documentation run (capture, compare, analyze).

**Endpoint**: `POST /functions/v1/process-run`

**Required Roles**: `admin`, `technical_writer`

**Request Body**:
```json
{
  "runId": "uuid"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Run processed successfully",
  "data": {
    "totalImages": 50,
    "changesDetected": 5
  }
}
```

**Error Response** (400/404/500):
```json
{
  "error": "Error message description"
}
```

---

## Error Responses

### Common Error Codes

**400 Bad Request**
```json
{
  "code": "PGRST102",
  "details": "Invalid input syntax",
  "message": "Error description"
}
```

**401 Unauthorized**
```json
{
  "message": "Invalid JWT token"
}
```

**403 Forbidden**
```json
{
  "message": "Permission denied"
}
```

**404 Not Found**
```json
{
  "message": "Resource not found"
}
```

**500 Internal Server Error**
```json
{
  "error": "Internal server error",
  "message": "Error description"
}
```

---

## Rate Limiting

Supabase applies rate limiting automatically:
- **Free tier**: 500 requests per second
- **Pro tier**: 1000 requests per second

When rate limited, you'll receive:
```json
{
  "message": "Rate limit exceeded"
}
```

Status Code: `429 Too Many Requests`

---

## Best Practices

### Pagination
Use `limit` and `offset` for large datasets:
```
GET /rest/v1/comparisons?limit=50&offset=100
```

### Filtering
Use PostgREST operators:
- `eq` - equals
- `neq` - not equals
- `gt` - greater than
- `lt` - less than
- `like` - pattern matching
- `in` - in list

Example:
```
GET /rest/v1/runs?status=in.(completed,failed)&project_id=eq.{uuid}
```

### Selecting Columns
Specify only needed columns:
```
GET /rest/v1/projects?select=id,name,status
```

### Nested Resources
Use foreign key relationships:
```
GET /rest/v1/runs?select=*,projects(name),user_profiles(email)
```

### Error Handling
Always check response status codes and handle errors appropriately:
```javascript
const response = await fetch(url, options);
if (!response.ok) {
  const error = await response.json();
  console.error('API Error:', error);
  throw new Error(error.message);
}
const data = await response.json();
```

---

## WebSocket Support

Real-time subscriptions are available via Supabase Realtime:

```javascript
const subscription = supabase
  .channel('runs-changes')
  .on('postgres_changes', {
    event: 'UPDATE',
    schema: 'public',
    table: 'runs'
  }, (payload) => {
    console.log('Run updated:', payload);
  })
  .subscribe();
```

---

## SDK Examples

### JavaScript/TypeScript

```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Create project
const { data, error } = await supabase
  .from('projects')
  .insert({
    name: 'My Project',
    app_type: 'web',
    comparison_tolerance: 98.0
  })
  .select()
  .single();

// List runs
const { data: runs } = await supabase
  .from('runs')
  .select('*, projects(name)')
  .eq('status', 'completed')
  .order('started_at', { ascending: false });

// Call edge function
const { data: result } = await supabase.functions.invoke('process-run', {
  body: { runId: 'uuid' }
});
```

### cURL

```bash
# List projects
curl -X GET 'https://[project-ref].supabase.co/rest/v1/projects' \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Create run
curl -X POST 'https://[project-ref].supabase.co/rest/v1/runs' \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "uuid",
    "status": "pending"
  }'

# Process run
curl -X POST 'https://[project-ref].supabase.co/functions/v1/process-run' \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"runId": "uuid"}'
```
