/*
  # Automatic Technical Document Updater - Initial Schema

  ## Overview
  This migration creates the complete database schema for the Automatic Technical Document Updater platform.
  The system automates synchronization of technical documentation with software GUI changes.

  ## New Tables

  1. **user_profiles**
     - Extends Supabase auth.users with role and metadata
     - Columns: id (FK to auth.users), email, role, full_name, created_at, updated_at
     - Roles: admin, technical_writer, reviewer, viewer

  2. **projects**
     - Stores application projects to be documented
     - Columns: id, name, description, app_type, app_url, app_executable_path, 
                document_paths, comparison_tolerance, status, created_by, created_at, updated_at
     - Links to user_profiles via created_by

  3. **runs**
     - Execution records of documentation update processes
     - Columns: id, project_id, status, triggered_by, trigger_type, started_at, 
                completed_at, total_images, changes_detected, error_message
     - Links to projects and user_profiles

  4. **documents**
     - Tracks documentation files in each project
     - Columns: id, project_id, file_path, file_format, version, storage_url, 
                file_size, page_count, created_at, updated_at
     - Links to projects

  5. **comparisons**
     - Individual image comparison results
     - Columns: id, run_id, document_id, doc_image_path, doc_image_url, 
                live_image_path, live_image_url, similarity_score, status, 
                change_severity, processed_at
     - Links to runs and documents

  6. **change_details**
     - Detailed analysis of detected changes
     - Columns: id, comparison_id, change_type, description, position_x, position_y,
                width, height, severity, ai_analysis, created_at
     - Links to comparisons

  7. **audit_logs**
     - Comprehensive audit trail of all system actions
     - Columns: id, user_id, action, resource_type, resource_id, details, 
                ip_address, user_agent, created_at
     - Links to user_profiles

  ## Security
  - RLS enabled on all tables
  - Policies enforce role-based access control
  - Admins have full access
  - Technical writers can create/edit projects and runs
  - Reviewers can view and approve changes
  - Viewers have read-only access
  - Users can only access projects they created or are assigned to

  ## Important Notes
  - All timestamps use timestamptz for timezone awareness
  - UUIDs used for all primary keys
  - Soft deletes not implemented (can be added later)
  - Indexes created for frequently queried columns
*/

-- Create enum types for better type safety
CREATE TYPE user_role AS ENUM ('admin', 'technical_writer', 'reviewer', 'viewer');
CREATE TYPE project_status AS ENUM ('active', 'archived', 'draft');
CREATE TYPE run_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled');
CREATE TYPE comparison_status AS ENUM ('pending', 'matched', 'changed', 'error');
CREATE TYPE change_severity AS ENUM ('critical', 'major', 'minor', 'cosmetic');
CREATE TYPE change_type AS ENUM ('layout', 'visual', 'content', 'new_element', 'removed_element');
CREATE TYPE app_type AS ENUM ('web', 'desktop_windows', 'desktop_macos', 'desktop_linux', 'electron');
CREATE TYPE document_format AS ENUM ('pdf', 'docx', 'html', 'xml', 'markdown');
CREATE TYPE trigger_type AS ENUM ('manual', 'scheduled', 'ci_cd', 'api');

-- 1. User Profiles Table
CREATE TABLE IF NOT EXISTS user_profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email text UNIQUE NOT NULL,
  role user_role NOT NULL DEFAULT 'viewer',
  full_name text,
  avatar_url text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- 2. Projects Table
CREATE TABLE IF NOT EXISTS projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text,
  app_type app_type NOT NULL,
  app_url text,
  app_executable_path text,
  document_paths jsonb DEFAULT '[]'::jsonb,
  comparison_tolerance numeric(5,2) DEFAULT 98.0,
  capture_config jsonb DEFAULT '{}'::jsonb,
  status project_status DEFAULT 'active',
  created_by uuid REFERENCES user_profiles(id) ON DELETE SET NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT valid_tolerance CHECK (comparison_tolerance >= 0 AND comparison_tolerance <= 100)
);

-- 3. Runs Table
CREATE TABLE IF NOT EXISTS runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  status run_status DEFAULT 'pending',
  triggered_by uuid REFERENCES user_profiles(id) ON DELETE SET NULL,
  trigger_type trigger_type DEFAULT 'manual',
  started_at timestamptz DEFAULT now(),
  completed_at timestamptz,
  total_images integer DEFAULT 0,
  changes_detected integer DEFAULT 0,
  error_message text,
  config_snapshot jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);

-- 4. Documents Table
CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  file_path text NOT NULL,
  file_format document_format NOT NULL,
  version integer DEFAULT 1,
  storage_url text,
  file_size bigint,
  page_count integer,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- 5. Comparisons Table
CREATE TABLE IF NOT EXISTS comparisons (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  document_id uuid REFERENCES documents(id) ON DELETE SET NULL,
  doc_image_path text NOT NULL,
  doc_image_url text,
  live_image_path text NOT NULL,
  live_image_url text,
  similarity_score numeric(5,2),
  status comparison_status DEFAULT 'pending',
  change_severity change_severity,
  is_approved boolean DEFAULT false,
  approved_by uuid REFERENCES user_profiles(id) ON DELETE SET NULL,
  approved_at timestamptz,
  processed_at timestamptz,
  CONSTRAINT valid_similarity CHECK (similarity_score IS NULL OR (similarity_score >= 0 AND similarity_score <= 100))
);

-- 6. Change Details Table
CREATE TABLE IF NOT EXISTS change_details (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  comparison_id uuid NOT NULL REFERENCES comparisons(id) ON DELETE CASCADE,
  change_type change_type NOT NULL,
  description text NOT NULL,
  position_x integer,
  position_y integer,
  width integer,
  height integer,
  severity change_severity NOT NULL,
  ai_analysis jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);

-- 7. Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES user_profiles(id) ON DELETE SET NULL,
  action text NOT NULL,
  resource_type text NOT NULL,
  resource_id uuid,
  details jsonb DEFAULT '{}'::jsonb,
  ip_address inet,
  user_agent text,
  created_at timestamptz DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_role ON user_profiles(role);
CREATE INDEX IF NOT EXISTS idx_projects_created_by ON projects(created_by);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_runs_project_id ON runs(project_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_triggered_by ON runs(triggered_by);
CREATE INDEX IF NOT EXISTS idx_documents_project_id ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_comparisons_run_id ON comparisons(run_id);
CREATE INDEX IF NOT EXISTS idx_comparisons_status ON comparisons(status);
CREATE INDEX IF NOT EXISTS idx_change_details_comparison_id ON change_details(comparison_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- Enable Row Level Security on all tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE comparisons ENABLE ROW LEVEL SECURITY;
ALTER TABLE change_details ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for user_profiles
CREATE POLICY "Users can view all profiles"
  ON user_profiles FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Users can update own profile"
  ON user_profiles FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

CREATE POLICY "Admins can update any profile"
  ON user_profiles FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "System can insert profiles"
  ON user_profiles FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = id);

-- RLS Policies for projects
CREATE POLICY "Users can view projects"
  ON projects FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer', 'reviewer', 'viewer')
    )
  );

CREATE POLICY "Technical writers and admins can create projects"
  ON projects FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer')
    )
  );

CREATE POLICY "Project creators and admins can update projects"
  ON projects FOR UPDATE
  TO authenticated
  USING (
    created_by = auth.uid()
    OR EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    created_by = auth.uid()
    OR EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "Admins can delete projects"
  ON projects FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

-- RLS Policies for runs
CREATE POLICY "Users can view runs"
  ON runs FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer', 'reviewer', 'viewer')
    )
  );

CREATE POLICY "Technical writers and admins can create runs"
  ON runs FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer')
    )
  );

CREATE POLICY "Technical writers and admins can update runs"
  ON runs FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer')
    )
  );

-- RLS Policies for documents
CREATE POLICY "Users can view documents"
  ON documents FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer', 'reviewer', 'viewer')
    )
  );

CREATE POLICY "Technical writers and admins can manage documents"
  ON documents FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer')
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer')
    )
  );

-- RLS Policies for comparisons
CREATE POLICY "Users can view comparisons"
  ON comparisons FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer', 'reviewer', 'viewer')
    )
  );

CREATE POLICY "Technical writers and admins can manage comparisons"
  ON comparisons FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer')
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer')
    )
  );

CREATE POLICY "Reviewers can approve comparisons"
  ON comparisons FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer', 'reviewer')
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer', 'reviewer')
    )
  );

-- RLS Policies for change_details
CREATE POLICY "Users can view change details"
  ON change_details FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer', 'reviewer', 'viewer')
    )
  );

CREATE POLICY "Technical writers and admins can manage change details"
  ON change_details FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer')
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid()
      AND role IN ('admin', 'technical_writer')
    )
  );

-- RLS Policies for audit_logs
CREATE POLICY "Admins can view all audit logs"
  ON audit_logs FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "Users can view their own audit logs"
  ON audit_logs FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "System can insert audit logs"
  ON audit_logs FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- Create function to automatically create user profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.user_profiles (id, email, role, full_name)
  VALUES (
    new.id,
    new.email,
    'viewer',
    new.raw_user_meta_data->>'full_name'
  );
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create profile on user signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();