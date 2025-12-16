# Deployment Guide

This guide covers deploying the Automatic Technical Document Updater to production.

## Prerequisites

- Supabase account
- Node.js 18+ installed
- Git repository

## Database Setup

The database schema is already applied to your Supabase instance. The following tables are configured:

- `user_profiles` - with RLS policies
- `projects` - with RLS policies
- `runs` - with RLS policies
- `documents` - with RLS policies
- `comparisons` - with RLS policies
- `change_details` - with RLS policies
- `audit_logs` - with RLS policies

All tables have Row Level Security enabled and appropriate policies configured.

## Environment Configuration

### Production Environment Variables

Create a `.env.production` file with:

```
VITE_SUPABASE_URL=your-production-supabase-url
VITE_SUPABASE_ANON_KEY=your-production-supabase-anon-key
```

### Supabase Configuration

1. **Enable Email Authentication**
   - Go to Authentication > Providers
   - Enable Email provider
   - Configure email templates (optional)
   - Disable email confirmation for easier onboarding (already configured)

2. **Configure Storage (Optional)**
   - Create a bucket named `documentation-images`
   - Set up CORS policies
   - Configure access policies

3. **Edge Functions**
   - The `process-run` function is already deployed
   - Verify it's accessible at: `{SUPABASE_URL}/functions/v1/process-run`

## Building for Production

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Run type checking**
   ```bash
   npm run typecheck
   ```

3. **Build the application**
   ```bash
   npm run build
   ```

4. **Test the production build**
   ```bash
   npm run preview
   ```

## Deployment Options

### Option 1: Vercel (Recommended)

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Deploy**
   ```bash
   vercel
   ```

3. **Configure environment variables**
   - Go to Vercel dashboard
   - Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
   - Redeploy

### Option 2: Netlify

1. **Install Netlify CLI**
   ```bash
   npm install -g netlify-cli
   ```

2. **Build and deploy**
   ```bash
   npm run build
   netlify deploy --prod --dir=dist
   ```

3. **Configure environment variables**
   - Go to Netlify dashboard
   - Site settings > Environment variables
   - Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY

### Option 3: Docker

1. **Create Dockerfile**
   ```dockerfile
   FROM node:18-alpine AS builder
   WORKDIR /app
   COPY package*.json ./
   RUN npm ci
   COPY . .
   RUN npm run build

   FROM nginx:alpine
   COPY --from=builder /app/dist /usr/share/nginx/html
   COPY nginx.conf /etc/nginx/conf.d/default.conf
   EXPOSE 80
   CMD ["nginx", "-g", "daemon off;"]
   ```

2. **Create nginx.conf**
   ```nginx
   server {
     listen 80;
     server_name _;
     root /usr/share/nginx/html;
     index index.html;

     location / {
       try_files $uri $uri/ /index.html;
     }
   }
   ```

3. **Build and run**
   ```bash
   docker build -t doc-updater .
   docker run -p 80:80 doc-updater
   ```

### Option 4: AWS S3 + CloudFront

1. **Build the application**
   ```bash
   npm run build
   ```

2. **Upload to S3**
   ```bash
   aws s3 sync dist/ s3://your-bucket-name --delete
   ```

3. **Configure CloudFront**
   - Create distribution pointing to S3 bucket
   - Set default root object to `index.html`
   - Configure error pages to redirect to `index.html`

## Post-Deployment Configuration

### 1. Create Admin User

After deployment, create your first admin user:

1. Sign up through the application
2. Use Supabase dashboard to update user role:
   ```sql
   UPDATE user_profiles
   SET role = 'admin'
   WHERE email = 'your-admin-email@example.com';
   ```

### 2. Configure CORS

Update Supabase CORS settings if needed:
- Go to Settings > API
- Add your production domain to allowed origins

### 3. Set Up Monitoring

Configure monitoring for:
- Edge function invocations
- Database query performance
- Authentication metrics
- Error rates

### 4. Configure Backups

Set up automated backups:
- Supabase provides automatic daily backups
- Configure point-in-time recovery
- Set up export schedules for audit logs

## Security Checklist

- [ ] Environment variables are not committed to repository
- [ ] HTTPS is enforced on production domain
- [ ] Database RLS policies are active
- [ ] Edge function JWT verification is enabled
- [ ] Admin user created and secured
- [ ] Audit logging is functioning
- [ ] CORS is properly configured
- [ ] Rate limiting is enabled (via Supabase)
- [ ] Secrets are stored securely

## Monitoring and Maintenance

### Health Checks

Monitor these metrics:
- API response times
- Database connection pool
- Edge function execution times
- Authentication success rate
- Storage usage

### Regular Maintenance

- Review audit logs weekly
- Check for failed runs
- Monitor disk usage
- Update dependencies monthly
- Review user roles quarterly

### Backup and Recovery

1. **Database Backups**
   - Supabase provides automatic backups
   - Download periodic exports
   - Test restore procedures

2. **Audit Log Exports**
   - Export logs monthly for compliance
   - Store in secure location
   - Maintain for required retention period

## Troubleshooting Production Issues

### High Database Load
- Review slow queries
- Add indexes if needed
- Optimize RLS policies
- Consider read replicas

### Edge Function Timeouts
- Increase timeout limits
- Optimize processing logic
- Consider async processing
- Use queue for long operations

### Authentication Issues
- Verify Supabase Auth settings
- Check JWT expiration settings
- Review CORS configuration
- Validate environment variables

## Scaling Considerations

### Database Scaling
- Monitor connection usage
- Consider upgrading Supabase plan
- Implement connection pooling
- Archive old data

### Application Scaling
- Deploy to multiple regions
- Use CDN for static assets
- Implement caching strategies
- Consider serverless deployment

### Storage Scaling
- Monitor storage usage
- Implement cleanup policies
- Use image optimization
- Consider archival strategies

## Cost Optimization

- Use appropriate Supabase plan
- Implement data retention policies
- Optimize edge function execution
- Monitor bandwidth usage
- Archive inactive projects

## Support and Updates

- Document all configuration changes
- Keep deployment documentation updated
- Maintain changelog
- Plan for zero-downtime updates
- Test updates in staging environment

## Rollback Procedure

If issues occur after deployment:

1. **Immediate Rollback**
   - Vercel: Revert to previous deployment
   - Netlify: Deploy previous version
   - Docker: Deploy previous image tag

2. **Database Rollback**
   - Restore from backup if schema changed
   - Run migration rollback scripts
   - Verify data integrity

3. **Verify Recovery**
   - Test authentication
   - Verify data access
   - Check audit logs
   - Monitor error rates

## Success Metrics

Track these KPIs post-deployment:
- User adoption rate
- Average processing time per run
- Change detection accuracy
- System uptime
- User satisfaction scores
- Cost per documentation update
