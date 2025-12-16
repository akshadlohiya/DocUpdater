import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import {
  Search,
  GitCompare,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
  Filter
} from 'lucide-react';
import type { Database } from '../lib/database.types';

type Comparison = Database['public']['Tables']['comparisons']['Row'] & {
  runs: {
    id: string;
    project_id: string;
    projects: {
      name: string;
    } | null;
  } | null;
};

export function Comparisons() {
  const [comparisons, setComparisons] = useState<Comparison[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  useEffect(() => {
    fetchComparisons();
  }, []);

  const fetchComparisons = async () => {
    try {
      const { data, error } = await supabase
        .from('comparisons')
        .select('*, runs(id, project_id, projects(name))')
        .order('processed_at', { ascending: false })
        .limit(100);

      if (error) throw error;
      setComparisons((data as Comparison[]) || []);
    } catch (error) {
      console.error('Error fetching comparisons:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredComparisons = comparisons.filter((comparison) => {
    const matchesSearch =
      comparison.doc_image_path.toLowerCase().includes(searchTerm.toLowerCase()) ||
      comparison.live_image_path.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = statusFilter === 'all' || comparison.status === statusFilter;
    const matchesSeverity =
      severityFilter === 'all' || comparison.change_severity === severityFilter;

    return matchesSearch && matchesStatus && matchesSeverity;
  });

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      pending: { bg: 'bg-gray-100', text: 'text-gray-700', icon: Clock },
      matched: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle },
      changed: { bg: 'bg-amber-100', text: 'text-amber-700', icon: AlertTriangle },
      error: { bg: 'bg-red-100', text: 'text-red-700', icon: XCircle },
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

  const getSeverityBadge = (severity: string | null) => {
    if (!severity) return null;

    const severityConfig = {
      critical: { bg: 'bg-red-100', text: 'text-red-700' },
      major: { bg: 'bg-orange-100', text: 'text-orange-700' },
      minor: { bg: 'bg-yellow-100', text: 'text-yellow-700' },
      cosmetic: { bg: 'bg-blue-100', text: 'text-blue-700' },
    };

    const config = severityConfig[severity as keyof typeof severityConfig];
    if (!config) return null;

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        {severity}
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
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Comparisons</h1>
        <p className="mt-2 text-gray-600">
          Review and approve documentation image comparisons
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by image path..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div className="flex flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-gray-400" />
            <span className="text-sm font-medium text-gray-700">Filters:</span>
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="matched">Matched</option>
            <option value="changed">Changed</option>
            <option value="error">Error</option>
          </select>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Severity</option>
            <option value="critical">Critical</option>
            <option value="major">Major</option>
            <option value="minor">Minor</option>
            <option value="cosmetic">Cosmetic</option>
          </select>

          {(statusFilter !== 'all' || severityFilter !== 'all') && (
            <button
              onClick={() => {
                setStatusFilter('all');
                setSeverityFilter('all');
              }}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900"
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {filteredComparisons.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <GitCompare className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {searchTerm || statusFilter !== 'all' || severityFilter !== 'all'
              ? 'No comparisons found'
              : 'No comparisons yet'}
          </h3>
          <p className="text-gray-600">
            {searchTerm || statusFilter !== 'all' || severityFilter !== 'all'
              ? 'Try adjusting your filters'
              : 'Run a project to generate image comparisons'}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Image Path
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Project
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Severity
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Similarity
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Approved
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredComparisons.map((comparison) => (
                  <tr key={comparison.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <Link
                        to={`/comparisons/${comparison.id}`}
                        className="text-sm font-medium text-blue-600 hover:text-blue-700"
                      >
                        {comparison.doc_image_path.split('/').pop() || comparison.doc_image_path}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {comparison.runs?.projects?.name || 'Unknown'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(comparison.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getSeverityBadge(comparison.change_severity)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {comparison.similarity_score !== null
                        ? `${comparison.similarity_score.toFixed(2)}%`
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {comparison.is_approved ? (
                        <CheckCircle className="w-5 h-5 text-green-600" />
                      ) : (
                        <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
