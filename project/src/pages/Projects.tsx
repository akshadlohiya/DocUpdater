import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { useAuth } from '../contexts/AuthContext';
import { logAudit } from '../utils/audit';
import {
  Plus,
  Search,
  FolderOpen,
  Globe,
  Monitor,
  AlertCircle,
  CheckCircle,
  Archive,
  Edit
} from 'lucide-react';
import type { Database } from '../lib/database.types';

type Project = Database['public']['Tables']['projects']['Row'] & {
  user_profiles: {
    full_name: string | null;
    email: string;
  } | null;
};

export function Projects() {
  const { hasRole } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const { data, error } = await supabase
        .from('projects')
        .select('*, user_profiles(full_name, email)')
        .order('created_at', { ascending: false });

      if (error) throw error;
      setProjects((data as Project[]) || []);
    } catch (error) {
      console.error('Error fetching projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredProjects = projects.filter((project) =>
    project.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (project.description && project.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const getAppTypeIcon = (appType: string) => {
    switch (appType) {
      case 'web':
        return <Globe className="w-5 h-5" />;
      default:
        return <Monitor className="w-5 h-5" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      active: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle },
      draft: { bg: 'bg-gray-100', text: 'text-gray-700', icon: Edit },
      archived: { bg: 'bg-gray-100', text: 'text-gray-700', icon: Archive },
    };

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.draft;
    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        <Icon className="w-3 h-3 mr-1" />
        {status}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
          <p className="mt-2 text-gray-600">
            Manage documentation projects and their configurations
          </p>
        </div>
        {hasRole(['admin', 'technical_writer']) && (
          <button
            onClick={() => setShowNewProjectModal(true)}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            <Plus className="w-5 h-5 mr-2" />
            New Project
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search projects..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {filteredProjects.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <FolderOpen className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {searchTerm ? 'No projects found' : 'No projects yet'}
          </h3>
          <p className="text-gray-600 mb-6">
            {searchTerm
              ? 'Try adjusting your search terms'
              : 'Create your first project to get started with automated documentation updates'}
          </p>
          {hasRole(['admin', 'technical_writer']) && !searchTerm && (
            <button
              onClick={() => setShowNewProjectModal(true)}
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
            >
              <Plus className="w-5 h-5 mr-2" />
              Create Project
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProjects.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 bg-blue-50 rounded-lg">
                  {getAppTypeIcon(project.app_type)}
                </div>
                {getStatusBadge(project.status)}
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {project.name}
              </h3>
              <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                {project.description || 'No description provided'}
              </p>
              <div className="flex items-center justify-between pt-4 border-t border-gray-100">
                <span className="text-xs text-gray-500 capitalize">
                  {project.app_type.replace('_', ' ')}
                </span>
                <span className="text-xs text-gray-500">
                  Tolerance: {project.comparison_tolerance}%
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {showNewProjectModal && (
        <NewProjectModal
          onClose={() => setShowNewProjectModal(false)}
          onSuccess={() => {
            setShowNewProjectModal(false);
            fetchProjects();
          }}
        />
      )}
    </div>
  );
}

interface NewProjectModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

function NewProjectModal({ onClose, onSuccess }: NewProjectModalProps) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    app_type: 'web' as const,
    app_url: '',
    app_executable_path: '',
    comparison_tolerance: 98,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const { error: insertError } = await supabase.from('projects').insert({
        name: formData.name,
        description: formData.description,
        app_type: formData.app_type,
        app_url: formData.app_url || null,
        app_executable_path: formData.app_executable_path || null,
        comparison_tolerance: formData.comparison_tolerance,
        created_by: user?.id,
        status: 'draft',
      });

      if (insertError) throw insertError;

      await logAudit('create', 'project', undefined, { name: formData.name });
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Create New Project</h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-start">
              <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Project Name *
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="My Application Documentation"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Brief description of this documentation project"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Application Type *
            </label>
            <select
              required
              value={formData.app_type}
              onChange={(e) => setFormData({ ...formData, app_type: e.target.value as any })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="web">Web Application</option>
              <option value="desktop_windows">Desktop - Windows</option>
              <option value="desktop_macos">Desktop - macOS</option>
              <option value="desktop_linux">Desktop - Linux</option>
              <option value="electron">Electron App</option>
            </select>
          </div>

          {formData.app_type === 'web' ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Application URL
              </label>
              <input
                type="url"
                value={formData.app_url}
                onChange={(e) => setFormData({ ...formData, app_url: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="https://example.com"
              />
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Executable Path
              </label>
              <input
                type="text"
                value={formData.app_executable_path}
                onChange={(e) => setFormData({ ...formData, app_executable_path: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="/path/to/application"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Comparison Tolerance (%)
            </label>
            <input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={formData.comparison_tolerance}
              onChange={(e) => setFormData({ ...formData, comparison_tolerance: parseFloat(e.target.value) })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="mt-1 text-sm text-gray-500">
              Images with similarity above this threshold are considered unchanged
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
            >
              {loading ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
