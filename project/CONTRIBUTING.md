# Contributing Guide

Thank you for your interest in contributing to the Automatic Technical Document Updater! This guide will help you get started with development and extending the system.

## Development Setup

### Prerequisites

- Node.js 18+
- npm or yarn
- Git
- Supabase CLI (optional, for database migrations)
- Code editor (VS Code recommended)

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd project
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

4. **Start development server**
   ```bash
   npm run dev
   ```

## Project Structure

```
project/
├── src/
│   ├── components/      # Reusable UI components
│   │   ├── Layout.tsx
│   │   └── ProtectedRoute.tsx
│   ├── contexts/        # React contexts (auth, etc.)
│   │   └── AuthContext.tsx
│   ├── lib/             # Library code and utilities
│   │   ├── supabase.ts
│   │   └── database.types.ts
│   ├── pages/           # Page components
│   │   ├── Dashboard.tsx
│   │   ├── Projects.tsx
│   │   ├── Comparisons.tsx
│   │   └── ...
│   ├── utils/           # Utility functions
│   │   └── audit.ts
│   ├── App.tsx          # Main app component
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles
├── supabase/
│   └── functions/       # Edge functions
│       └── process-run/
├── public/              # Static assets
├── docs/                # Documentation
├── .env.example         # Example environment variables
└── package.json
```

## Development Workflow

### 1. Create a New Feature

```bash
# Create a new branch
git checkout -b feature/your-feature-name

# Make your changes
# ...

# Test your changes
npm run build
npm run typecheck

# Commit your changes
git add .
git commit -m "Add: your feature description"

# Push to repository
git push origin feature/your-feature-name
```

### 2. Code Style

This project uses:
- **TypeScript** for type safety
- **ESLint** for code quality
- **Tailwind CSS** for styling
- **React Hooks** for state management

#### TypeScript Guidelines

```typescript
// Use explicit types
interface Project {
  id: string;
  name: string;
  description: string | null;
}

// Prefer const over let
const project: Project = { ... };

// Use optional chaining
const name = project?.user?.full_name ?? 'Unknown';

// Use async/await instead of promises
const data = await fetchData();
```

#### React Guidelines

```tsx
// Use functional components with TypeScript
export function MyComponent({ prop }: { prop: string }) {
  const [state, setState] = useState<string>('');

  useEffect(() => {
    // Side effects here
  }, [dependencies]);

  return <div>{prop}</div>;
}

// Extract complex logic to custom hooks
function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    fetchProjects();
  }, []);

  return { projects };
}
```

#### Styling Guidelines

```tsx
// Use Tailwind classes
<div className="bg-white rounded-xl shadow-sm p-6">
  <h2 className="text-lg font-semibold text-gray-900">Title</h2>
</div>

// Keep classes organized: layout → spacing → colors → typography
<button className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
  Click me
</button>
```

### 3. Adding New Pages

1. Create page component in `src/pages/`
2. Add route in `src/App.tsx`
3. Add navigation link in `src/components/Layout.tsx`
4. Update RLS policies if needed

Example:
```tsx
// src/pages/MyNewPage.tsx
export function MyNewPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold">My New Page</h1>
      {/* Page content */}
    </div>
  );
}

// src/App.tsx
<Route
  path="/my-page"
  element={
    <ProtectedRoute>
      <Layout>
        <MyNewPage />
      </Layout>
    </ProtectedRoute>
  }
/>
```

### 4. Database Changes

When adding new tables or columns:

1. **Create migration file**
   ```sql
   -- supabase/migrations/20240101_add_feature.sql
   CREATE TABLE new_table (
     id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
     name text NOT NULL,
     created_at timestamptz DEFAULT now()
   );

   ALTER TABLE new_table ENABLE ROW LEVEL SECURITY;

   CREATE POLICY "Users can view own data"
     ON new_table FOR SELECT
     TO authenticated
     USING (auth.uid() = user_id);
   ```

2. **Update TypeScript types**
   ```typescript
   // src/lib/database.types.ts
   export interface Database {
     public: {
       Tables: {
         new_table: {
           Row: {
             id: string;
             name: string;
             created_at: string;
           };
           // Insert and Update types
         };
       };
     };
   }
   ```

3. **Test migration locally**
   - Apply to development database
   - Verify RLS policies work
   - Test CRUD operations

### 5. Adding Edge Functions

1. **Create function directory**
   ```bash
   mkdir -p supabase/functions/my-function
   ```

2. **Create index.ts**
   ```typescript
   import "jsr:@supabase/functions-js/edge-runtime.d.ts";

   const corsHeaders = {
     "Access-Control-Allow-Origin": "*",
     "Access-Control-Allow-Methods": "POST",
     "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey",
   };

   Deno.serve(async (req: Request) => {
     if (req.method === "OPTIONS") {
       return new Response(null, {
         status: 200,
         headers: corsHeaders,
       });
     }

     try {
       const { data } = await req.json();

       // Your logic here

       return new Response(
         JSON.stringify({ success: true, data }),
         {
           headers: {
             ...corsHeaders,
             "Content-Type": "application/json",
           },
         }
       );
     } catch (error) {
       return new Response(
         JSON.stringify({ error: error.message }),
         {
           status: 500,
           headers: {
             ...corsHeaders,
             "Content-Type": "application/json",
           },
         }
       );
     }
   });
   ```

3. **Deploy function**
   - Use the Supabase dashboard
   - Or deploy programmatically

4. **Test function**
   ```bash
   curl -X POST 'https://[project].supabase.co/functions/v1/my-function' \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"data": "test"}'
   ```

## Extension Points

### 1. Adding New Document Formats

Create a parser for new formats:

```typescript
// src/utils/parsers/MyFormatParser.ts
export class MyFormatParser {
  async parse(filePath: string) {
    // Parse document
    return {
      images: [],
      metadata: {},
    };
  }

  async update(filePath: string, updates: Update[]) {
    // Update document
  }
}
```

### 2. Adding New Application Types

Update the enum and add capture logic:

```sql
-- Migration
ALTER TYPE app_type ADD VALUE 'my_app_type';
```

```typescript
// Edge function
if (project.app_type === 'my_app_type') {
  // Custom capture logic
}
```

### 3. Custom Comparison Algorithms

Extend the comparison engine:

```typescript
// src/utils/comparison/CustomAlgorithm.ts
export class CustomAlgorithm {
  compare(image1: Buffer, image2: Buffer): ComparisonResult {
    // Custom comparison logic
    return {
      score: 95.5,
      changes: [],
    };
  }
}
```

### 4. New AI/ML Models

Integrate new models for change detection:

```typescript
// src/utils/ml/ChangeDetector.ts
export class ChangeDetector {
  async analyze(image1: string, image2: string) {
    // ML model integration
    return {
      changeType: 'layout',
      confidence: 0.95,
      description: 'Button moved 10px right',
    };
  }
}
```

## Testing

### Unit Tests

```typescript
// src/utils/__tests__/audit.test.ts
import { describe, it, expect } from 'vitest';
import { logAudit } from '../audit';

describe('Audit Logger', () => {
  it('should log actions', async () => {
    await logAudit('create', 'project', 'uuid');
    // Assert log was created
  });
});
```

### Integration Tests

```typescript
// src/__tests__/projects.test.ts
describe('Projects API', () => {
  it('should create project', async () => {
    const project = await createProject({
      name: 'Test Project',
      app_type: 'web',
    });
    expect(project.id).toBeDefined();
  });
});
```

## Performance Optimization

### Database Queries

```typescript
// Bad: N+1 queries
for (const run of runs) {
  const project = await fetchProject(run.project_id);
}

// Good: Single query with join
const runs = await supabase
  .from('runs')
  .select('*, projects(*)')
  .eq('status', 'completed');
```

### React Performance

```tsx
// Use memo for expensive computations
const filteredData = useMemo(
  () => data.filter(item => item.active),
  [data]
);

// Use callback for event handlers
const handleClick = useCallback(() => {
  // Handler logic
}, [dependencies]);
```

## Security Considerations

### 1. Input Validation

```typescript
// Validate all user input
if (!email || !isValidEmail(email)) {
  throw new Error('Invalid email');
}

// Sanitize for database
const safeName = name.trim().substring(0, 255);
```

### 2. RLS Policies

Always test RLS policies:

```sql
-- Test as different users
SET request.jwt.claim.sub TO 'user-uuid';
SELECT * FROM projects; -- Should only see user's projects
```

### 3. API Security

```typescript
// Always verify authentication
const user = await supabase.auth.getUser();
if (!user) throw new Error('Unauthorized');

// Check permissions
if (!hasPermission(user, 'create_project')) {
  throw new Error('Forbidden');
}
```

## Documentation

When adding features, update:

1. **README.md** - High-level overview
2. **API.md** - API endpoints
3. **DEPLOYMENT.md** - Deployment steps
4. **Code comments** - Complex logic
5. **Type definitions** - All interfaces

## Commit Guidelines

Use conventional commits:

```
feat: Add new document format parser
fix: Resolve RLS policy bug
docs: Update API documentation
style: Format code with prettier
refactor: Simplify comparison logic
test: Add tests for audit logging
chore: Update dependencies
```

## Pull Request Process

1. **Create descriptive PR**
   - Clear title
   - Detailed description
   - Link to related issues

2. **Ensure CI passes**
   - Build succeeds
   - Tests pass
   - Linting passes

3. **Request review**
   - Tag relevant reviewers
   - Respond to feedback
   - Update as needed

4. **Merge**
   - Squash commits if needed
   - Delete branch after merge

## Getting Help

- **Questions**: Open a discussion
- **Bugs**: Open an issue
- **Features**: Open a feature request
- **Security**: Email security@example.com

## Resources

- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Supabase Documentation](https://supabase.com/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)

Thank you for contributing!
