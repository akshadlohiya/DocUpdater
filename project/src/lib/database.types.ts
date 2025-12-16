export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type UserRole = 'admin' | 'technical_writer' | 'reviewer' | 'viewer';
export type ProjectStatus = 'active' | 'archived' | 'draft';
export type RunStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
export type ComparisonStatus = 'pending' | 'matched' | 'changed' | 'error';
export type ChangeSeverity = 'critical' | 'major' | 'minor' | 'cosmetic';
export type ChangeType = 'layout' | 'visual' | 'content' | 'new_element' | 'removed_element';
export type AppType = 'web' | 'desktop_windows' | 'desktop_macos' | 'desktop_linux' | 'electron';
export type DocumentFormat = 'pdf' | 'docx' | 'html' | 'xml' | 'markdown';
export type TriggerType = 'manual' | 'scheduled' | 'ci_cd' | 'api';

export interface Database {
  public: {
    Tables: {
      user_profiles: {
        Row: {
          id: string;
          email: string;
          role: UserRole;
          full_name: string | null;
          avatar_url: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id: string;
          email: string;
          role?: UserRole;
          full_name?: string | null;
          avatar_url?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          email?: string;
          role?: UserRole;
          full_name?: string | null;
          avatar_url?: string | null;
          created_at?: string;
          updated_at?: string;
        };
      };
      projects: {
        Row: {
          id: string;
          name: string;
          description: string | null;
          app_type: AppType;
          app_url: string | null;
          app_executable_path: string | null;
          document_paths: Json;
          comparison_tolerance: number;
          capture_config: Json;
          status: ProjectStatus;
          created_by: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          name: string;
          description?: string | null;
          app_type: AppType;
          app_url?: string | null;
          app_executable_path?: string | null;
          document_paths?: Json;
          comparison_tolerance?: number;
          capture_config?: Json;
          status?: ProjectStatus;
          created_by?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          name?: string;
          description?: string | null;
          app_type?: AppType;
          app_url?: string | null;
          app_executable_path?: string | null;
          document_paths?: Json;
          comparison_tolerance?: number;
          capture_config?: Json;
          status?: ProjectStatus;
          created_by?: string | null;
          created_at?: string;
          updated_at?: string;
        };
      };
      runs: {
        Row: {
          id: string;
          project_id: string;
          status: RunStatus;
          triggered_by: string | null;
          trigger_type: TriggerType;
          started_at: string;
          completed_at: string | null;
          total_images: number;
          changes_detected: number;
          error_message: string | null;
          config_snapshot: Json;
          created_at: string;
        };
        Insert: {
          id?: string;
          project_id: string;
          status?: RunStatus;
          triggered_by?: string | null;
          trigger_type?: TriggerType;
          started_at?: string;
          completed_at?: string | null;
          total_images?: number;
          changes_detected?: number;
          error_message?: string | null;
          config_snapshot?: Json;
          created_at?: string;
        };
        Update: {
          id?: string;
          project_id?: string;
          status?: RunStatus;
          triggered_by?: string | null;
          trigger_type?: TriggerType;
          started_at?: string;
          completed_at?: string | null;
          total_images?: number;
          changes_detected?: number;
          error_message?: string | null;
          config_snapshot?: Json;
          created_at?: string;
        };
      };
      documents: {
        Row: {
          id: string;
          project_id: string;
          file_path: string;
          file_format: DocumentFormat;
          version: number;
          storage_url: string | null;
          file_size: number | null;
          page_count: number | null;
          metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          project_id: string;
          file_path: string;
          file_format: DocumentFormat;
          version?: number;
          storage_url?: string | null;
          file_size?: number | null;
          page_count?: number | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          project_id?: string;
          file_path?: string;
          file_format?: DocumentFormat;
          version?: number;
          storage_url?: string | null;
          file_size?: number | null;
          page_count?: number | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
      };
      comparisons: {
        Row: {
          id: string;
          run_id: string;
          document_id: string | null;
          doc_image_path: string;
          doc_image_url: string | null;
          live_image_path: string;
          live_image_url: string | null;
          similarity_score: number | null;
          status: ComparisonStatus;
          change_severity: ChangeSeverity | null;
          is_approved: boolean;
          approved_by: string | null;
          approved_at: string | null;
          processed_at: string | null;
        };
        Insert: {
          id?: string;
          run_id: string;
          document_id?: string | null;
          doc_image_path: string;
          doc_image_url?: string | null;
          live_image_path: string;
          live_image_url?: string | null;
          similarity_score?: number | null;
          status?: ComparisonStatus;
          change_severity?: ChangeSeverity | null;
          is_approved?: boolean;
          approved_by?: string | null;
          approved_at?: string | null;
          processed_at?: string | null;
        };
        Update: {
          id?: string;
          run_id?: string;
          document_id?: string | null;
          doc_image_path?: string;
          doc_image_url?: string | null;
          live_image_path?: string;
          live_image_url?: string | null;
          similarity_score?: number | null;
          status?: ComparisonStatus;
          change_severity?: ChangeSeverity | null;
          is_approved?: boolean;
          approved_by?: string | null;
          approved_at?: string | null;
          processed_at?: string | null;
        };
      };
      change_details: {
        Row: {
          id: string;
          comparison_id: string;
          change_type: ChangeType;
          description: string;
          position_x: number | null;
          position_y: number | null;
          width: number | null;
          height: number | null;
          severity: ChangeSeverity;
          ai_analysis: Json;
          created_at: string;
        };
        Insert: {
          id?: string;
          comparison_id: string;
          change_type: ChangeType;
          description: string;
          position_x?: number | null;
          position_y?: number | null;
          width?: number | null;
          height?: number | null;
          severity: ChangeSeverity;
          ai_analysis?: Json;
          created_at?: string;
        };
        Update: {
          id?: string;
          comparison_id?: string;
          change_type?: ChangeType;
          description?: string;
          position_x?: number | null;
          position_y?: number | null;
          width?: number | null;
          height?: number | null;
          severity?: ChangeSeverity;
          ai_analysis?: Json;
          created_at?: string;
        };
      };
      audit_logs: {
        Row: {
          id: string;
          user_id: string | null;
          action: string;
          resource_type: string;
          resource_id: string | null;
          details: Json;
          ip_address: string | null;
          user_agent: string | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          user_id?: string | null;
          action: string;
          resource_type: string;
          resource_id?: string | null;
          details?: Json;
          ip_address?: string | null;
          user_agent?: string | null;
          created_at?: string;
        };
        Update: {
          id?: string;
          user_id?: string | null;
          action?: string;
          resource_type?: string;
          resource_id?: string | null;
          details?: Json;
          ip_address?: string | null;
          user_agent?: string | null;
          created_at?: string;
        };
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      [_ in never]: never;
    };
    Enums: {
      user_role: UserRole;
      project_status: ProjectStatus;
      run_status: RunStatus;
      comparison_status: ComparisonStatus;
      change_severity: ChangeSeverity;
      change_type: ChangeType;
      app_type: AppType;
      document_format: DocumentFormat;
      trigger_type: TriggerType;
    };
  };
}
