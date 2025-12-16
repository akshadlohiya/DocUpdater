import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { useAuth } from '../contexts/AuthContext';
import { logAudit } from '../utils/audit';
import {
  ArrowLeft,
  Play,
  Settings,
  FileText,
  Clock,
  CheckCircle,
  AlertCircle,
  PlayCircle,
  Edit,
  Archive
} from 'lucide-react';
import type { Database } from '../lib/database.types';

type Project = Database['public']['Tables']['projects']['Row'];
type Run = Database['public']['Tables']['runs']['Row'];

const useEdgeSimulation = import.meta.env.VITE_USE_EDGE_SIMULATION !== 'false';

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const { hasRole } = useAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [startingRun, setStartingRun] = useState(false);

  useEffect(() => {
    if (id) {
      fetchProjectData();
    }
  }, [id]);

  const fetchProjectData = async () => {
    try {
      const [projectRes, runsRes] = await Promise.all([
        supabase.from('projects').select('*').eq('id', id).maybeSingle(),
        supabase
          .from('runs')
          .select('*')
          .eq('project_id', id)
          .order('started_at', { ascending: false }),
      ]);

      if (projectRes.error) throw projectRes.error;
      if (runsRes.error) throw runsRes.error;

      setProject(projectRes.data);
      setRuns(runsRes.data || []);
    } catch (error) {
      console.error('Error fetching project data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartRun = async () => {
    if (!id || !project) return;

    setStartingRun(true);
    try {
      const { data: { user } } = await supabase.auth.getUser();

      const { data: insertedRun, error } = await supabase
        .from('runs')
        .insert({
          project_id: id,
          status: 'pending',
          triggered_by: user?.id,
          trigger_type: 'manual',
          config_snapshot: {
            tolerance: project.comparison_tolerance,
            app_type: project.app_type,
          },
        })
        .select()
        .single();

      if (error) throw error;

      // Log audit and refresh project data immediately
      await logAudit('start_run', 'run', insertedRun?.id || id, { project_name: project.name });
      fetchProjectData();

      // Invoke the process-run edge function to start processing this run.
      // This uses the Supabase Functions HTTP endpoint and relies on CORS being allowed.
      try {
        const runId = insertedRun?.id || id;
        if (useEdgeSimulation) {
          // Fire-and-forget; invoke via Supabase Functions so Authorization is included
          supabase.functions
            .invoke('process-run', { body: { runId } })
            .catch((err) => console.error('Failed to invoke process-run function', err));
        }
      } catch (err) {
        console.error('Error invoking process-run function:', err);
      }
    } catch (error) {
      console.error('Error starting run:', error);
      alert('Failed to start run. Please try again.');
    } finally {
      setStartingRun(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      pending: { bg: 'bg-gray-100', text: 'text-gray-700', icon: Clock },
      processing: { bg: 'bg-blue-100', text: 'text-blue-700', icon: PlayCircle },
      completed: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle },
      failed: { bg: 'bg-red-100', text: 'text-red-700', icon: AlertCircle },
      cancelled: { bg: 'bg-gray-100', text: 'text-gray-700', icon: AlertCircle },
    };

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        <Icon className="w-3 h-3 mr-1" />
        {status}
      </span>
    );
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDuration = (start: string, end: string | null) => {
    if (!end) return 'In progress';
    const duration = new Date(end).getTime() - new Date(start).getTime();
    const minutes = Math.floor(duration / 60000);
    const seconds = Math.floor((duration % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Project not found</h3>
        <Link to="/projects" className="text-blue-600 hover:text-blue-700">
          Back to projects
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link
          to="/projects"
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </Link>
        <div className="flex-1">
          <h1 className="text-3xl font-bold text-gray-900">{project.name}</h1>
          {project.description && (
            <p className="mt-2 text-gray-600">{project.description}</p>
          )}
        </div>
        {hasRole(['admin', 'technical_writer']) && (
          <button
            onClick={handleStartRun}
            disabled={startingRun}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
          >
            <Play className="w-5 h-5 mr-2" />
            {startingRun ? 'Starting...' : 'Start Run'}
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600">Project Details</h3>
            <Settings className="w-5 h-5 text-gray-400" />
          </div>
          <dl className="space-y-3">
            <div>
              <dt className="text-xs text-gray-500">Application Type</dt>
              <dd className="text-sm font-medium text-gray-900 capitalize mt-1">
                {project.app_type.replace('_', ' ')}
              </dd>
            </div>
            {project.app_url && (
              <div>
                <dt className="text-xs text-gray-500">URL</dt>
                <dd className="text-sm font-medium text-gray-900 mt-1 truncate">
                  {project.app_url}
                </dd>
              </div>
            )}
            <div>
              <dt className="text-xs text-gray-500">Comparison Tolerance</dt>
              <dd className="text-sm font-medium text-gray-900 mt-1">
                {project.comparison_tolerance}%
              </dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500">Status</dt>
              <dd className="mt-1">
                {project.status === 'active' && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                    <CheckCircle className="w-3 h-3 mr-1" />
                    Active
                  </span>
                )}
                {project.status === 'draft' && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                    <Edit className="w-3 h-3 mr-1" />
                    Draft
                  </span>
                )}
                {project.status === 'archived' && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                    <Archive className="w-3 h-3 mr-1" />
                    Archived
                  </span>
                )}
              </dd>
            </div>
          </dl>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600">Statistics</h3>
            <FileText className="w-5 h-5 text-gray-400" />
          </div>
          <dl className="space-y-3">
            <div>
              <dt className="text-xs text-gray-500">Total Runs</dt>
              <dd className="text-2xl font-bold text-gray-900 mt-1">{runs.length}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500">Completed Runs</dt>
              <dd className="text-2xl font-bold text-gray-900 mt-1">
                {runs.filter((r) => r.status === 'completed').length}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500">Total Changes Detected</dt>
              <dd className="text-2xl font-bold text-gray-900 mt-1">
                {runs.reduce((sum, r) => sum + r.changes_detected, 0)}
              </dd>
            </div>
          </dl>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600">Last Run</h3>
            <Clock className="w-5 h-5 text-gray-400" />
          </div>
          {runs.length > 0 ? (
            <dl className="space-y-3">
              <div>
                <dt className="text-xs text-gray-500">Status</dt>
                <dd className="mt-1">{getStatusBadge(runs[0].status)}</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500">Started</dt>
                <dd className="text-sm font-medium text-gray-900 mt-1">
                  {formatDate(runs[0].started_at)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500">Duration</dt>
                <dd className="text-sm font-medium text-gray-900 mt-1">
                  {formatDuration(runs[0].started_at, runs[0].completed_at)}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-gray-500">No runs yet</p>
          )}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Run History</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Started
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Images
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Changes
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {runs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                    No runs yet. Click "Start Run" to begin your first documentation update.
                  </td>
                </tr>
              ) : (
                runs.map((run) => (
                  <tr key={run.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(run.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {formatDate(run.started_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {formatDuration(run.started_at, run.completed_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {run.total_images}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {run.changes_detected > 0 ? (
                        <span className="text-amber-600 font-medium">{run.changes_detected}</span>
                      ) : (
                        <span className="text-gray-400">0</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 capitalize">
                      {run.trigger_type}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
