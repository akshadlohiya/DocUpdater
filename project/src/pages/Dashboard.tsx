import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { useAuth } from '../contexts/AuthContext';
import {
  FolderOpen,
  PlayCircle,
  GitCompare,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Clock,
  Plus
} from 'lucide-react';

interface Stats {
  totalProjects: number;
  activeRuns: number;
  totalComparisons: number;
  changesDetected: number;
}

interface RecentRun {
  id: string;
  project_id: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  total_images: number;
  changes_detected: number;
  projects: {
    name: string;
  } | null;
}

export function Dashboard() {
  const { profile, hasRole } = useAuth();
  const [stats, setStats] = useState<Stats>({
    totalProjects: 0,
    activeRuns: 0,
    totalComparisons: 0,
    changesDetected: 0,
  });
  const [recentRuns, setRecentRuns] = useState<RecentRun[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [projectsRes, runsRes, comparisonsRes, recentRunsRes] = await Promise.all([
        supabase.from('projects').select('id', { count: 'exact', head: true }),
        supabase.from('runs').select('id', { count: 'exact', head: true }).eq('status', 'processing'),
        supabase.from('comparisons').select('id, status', { count: 'exact', head: true }),
        supabase
          .from('runs')
          .select('id, project_id, status, started_at, completed_at, total_images, changes_detected, projects(name)')
          .order('started_at', { ascending: false })
          .limit(5),
      ]);

      const changesCount = await supabase
        .from('comparisons')
        .select('id', { count: 'exact', head: true })
        .eq('status', 'changed');

      setStats({
        totalProjects: projectsRes.count || 0,
        activeRuns: runsRes.count || 0,
        totalComparisons: comparisonsRes.count || 0,
        changesDetected: changesCount.count || 0,
      });

      setRecentRuns((recentRunsRes.data as RecentRun[]) || []);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
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
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-2 text-gray-600">
            Welcome back, {profile?.full_name || profile?.email}
          </p>
        </div>
        {hasRole(['admin', 'technical_writer']) && (
          <Link
            to="/projects"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            <Plus className="w-5 h-5 mr-2" />
            New Project
          </Link>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Projects</p>
              <p className="mt-2 text-3xl font-bold text-gray-900">{stats.totalProjects}</p>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg">
              <FolderOpen className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Active Runs</p>
              <p className="mt-2 text-3xl font-bold text-gray-900">{stats.activeRuns}</p>
            </div>
            <div className="p-3 bg-green-50 rounded-lg">
              <PlayCircle className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Comparisons</p>
              <p className="mt-2 text-3xl font-bold text-gray-900">{stats.totalComparisons}</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg">
              <GitCompare className="w-6 h-6 text-slate-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Changes Detected</p>
              <p className="mt-2 text-3xl font-bold text-gray-900">{stats.changesDetected}</p>
            </div>
            <div className="p-3 bg-amber-50 rounded-lg">
              <TrendingUp className="w-6 h-6 text-amber-600" />
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Runs</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Project
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Started
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Images
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Changes
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {recentRuns.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                    No runs yet. Create a project and start your first run.
                  </td>
                </tr>
              ) : (
                recentRuns.map((run) => (
                  <tr key={run.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        to={`/projects/${run.project_id}`}
                        className="text-sm font-medium text-blue-600 hover:text-blue-700"
                      >
                        {run.projects?.name || 'Unknown Project'}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(run.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {formatDate(run.started_at)}
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
