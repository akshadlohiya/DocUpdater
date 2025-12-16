import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { useAuth } from '../contexts/AuthContext';
import { logAudit } from '../utils/audit';
import {
  ArrowLeft,
  Check,
  X,
  AlertCircle,
  CheckCircle,
  Info
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

type ChangeDetail = Database['public']['Tables']['change_details']['Row'];

export function ComparisonDetail() {
  const { id } = useParams<{ id: string }>();
  const { hasRole, user } = useAuth();
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [changeDetails, setChangeDetails] = useState<ChangeDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);

  useEffect(() => {
    if (id) {
      fetchComparisonData();
    }
  }, [id]);

  const fetchComparisonData = async () => {
    try {
      const [comparisonRes, changesRes] = await Promise.all([
        supabase
          .from('comparisons')
          .select('*, runs(id, project_id, projects(name))')
          .eq('id', id)
          .maybeSingle(),
        supabase
          .from('change_details')
          .select('*')
          .eq('comparison_id', id)
          .order('created_at', { ascending: false }),
      ]);

      if (comparisonRes.error) throw comparisonRes.error;
      if (changesRes.error) throw changesRes.error;

      setComparison(comparisonRes.data as Comparison);
      setChangeDetails(changesRes.data || []);
    } catch (error) {
      console.error('Error fetching comparison data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (approved: boolean) => {
    if (!comparison || !user) return;

    setApproving(true);
    try {
      const { error } = await supabase
        .from('comparisons')
        .update({
          is_approved: approved,
          approved_by: user.id,
          approved_at: new Date().toISOString(),
        })
        .eq('id', comparison.id);

      if (error) throw error;

      await logAudit(
        approved ? 'approve_comparison' : 'reject_comparison',
        'comparison',
        comparison.id,
        { doc_image_path: comparison.doc_image_path }
      );

      fetchComparisonData();
    } catch (error) {
      console.error('Error approving comparison:', error);
      alert('Failed to update approval status. Please try again.');
    } finally {
      setApproving(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      pending: { bg: 'bg-gray-100', text: 'text-gray-700' },
      matched: { bg: 'bg-green-100', text: 'text-green-700' },
      changed: { bg: 'bg-amber-100', text: 'text-amber-700' },
      error: { bg: 'bg-red-100', text: 'text-red-700' },
    };

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        {status}
      </span>
    );
  };

  const getSeverityColor = (severity: string) => {
    const colors = {
      critical: 'text-red-600',
      major: 'text-orange-600',
      minor: 'text-yellow-600',
      cosmetic: 'text-blue-600',
    };
    return colors[severity as keyof typeof colors] || 'text-gray-600';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!comparison) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Comparison not found</h3>
        <Link to="/comparisons" className="text-blue-600 hover:text-blue-700">
          Back to comparisons
        </Link>
      </div>
    );
  }

  const canApprove = hasRole(['admin', 'technical_writer', 'reviewer']);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link
          to="/comparisons"
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">Image Comparison</h1>
          <p className="text-gray-600 mt-1">{comparison.doc_image_path}</p>
        </div>
        {canApprove && !comparison.is_approved && (
          <div className="flex gap-2">
            <button
              onClick={() => handleApprove(false)}
              disabled={approving}
              className="inline-flex items-center px-4 py-2 border border-red-300 text-red-700 rounded-lg hover:bg-red-50 disabled:opacity-50 font-medium"
            >
              <X className="w-5 h-5 mr-2" />
              Reject
            </button>
            <button
              onClick={() => handleApprove(true)}
              disabled={approving}
              className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium"
            >
              <Check className="w-5 h-5 mr-2" />
              Approve
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-4">Comparison Details</h3>
          <dl className="space-y-3">
            <div>
              <dt className="text-xs text-gray-500">Project</dt>
              <dd className="text-sm font-medium text-gray-900 mt-1">
                <Link
                  to={`/projects/${comparison.runs?.project_id}`}
                  className="text-blue-600 hover:text-blue-700"
                >
                  {comparison.runs?.projects?.name || 'Unknown'}
                </Link>
              </dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500">Status</dt>
              <dd className="mt-1">{getStatusBadge(comparison.status)}</dd>
            </div>
            {comparison.similarity_score !== null && (
              <div>
                <dt className="text-xs text-gray-500">Similarity Score</dt>
                <dd className="text-sm font-medium text-gray-900 mt-1">
                  {comparison.similarity_score.toFixed(2)}%
                </dd>
              </div>
            )}
            {comparison.change_severity && (
              <div>
                <dt className="text-xs text-gray-500">Severity</dt>
                <dd className={`text-sm font-medium mt-1 capitalize ${getSeverityColor(comparison.change_severity)}`}>
                  {comparison.change_severity}
                </dd>
              </div>
            )}
            <div>
              <dt className="text-xs text-gray-500">Approval Status</dt>
              <dd className="mt-1">
                {comparison.is_approved ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                    <CheckCircle className="w-3 h-3 mr-1" />
                    Approved
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                    Pending Review
                  </span>
                )}
              </dd>
            </div>
          </dl>
        </div>

        <div className="md:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-4">File Paths</h3>
          <dl className="space-y-3">
            <div>
              <dt className="text-xs text-gray-500 mb-1">Documentation Image</dt>
              <dd className="text-sm text-gray-900 font-mono bg-gray-50 p-2 rounded border border-gray-200 break-all">
                {comparison.doc_image_path}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500 mb-1">Live Screenshot</dt>
              <dd className="text-sm text-gray-900 font-mono bg-gray-50 p-2 rounded border border-gray-200 break-all">
                {comparison.live_image_path}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Side-by-Side Comparison</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">Documentation Image</h4>
            <div className="border-2 border-gray-200 rounded-lg overflow-hidden bg-gray-50 aspect-video flex items-center justify-center">
              {comparison.doc_image_url ? (
                <img
                  src={comparison.doc_image_url}
                  alt="Documentation"
                  className="max-w-full max-h-full object-contain"
                />
              ) : (
                <div className="text-center p-8">
                  <Info className="w-12 h-12 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">Image not available</p>
                </div>
              )}
            </div>
          </div>
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">Live Screenshot</h4>
            <div className="border-2 border-gray-200 rounded-lg overflow-hidden bg-gray-50 aspect-video flex items-center justify-center">
              {comparison.live_image_url ? (
                <img
                  src={comparison.live_image_url}
                  alt="Live Screenshot"
                  className="max-w-full max-h-full object-contain"
                />
              ) : (
                <div className="text-center p-8">
                  <Info className="w-12 h-12 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">Image not available</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {changeDetails.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Detected Changes</h3>
          </div>
          <div className="p-6 space-y-4">
            {changeDetails.map((change) => (
              <div
                key={change.id}
                className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${getSeverityColor(change.severity)} bg-gray-50`}>
                      {change.severity}
                    </span>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 capitalize">
                      {change.change_type.replace('_', ' ')}
                    </span>
                  </div>
                  {change.position_x !== null && change.position_y !== null && (
                    <span className="text-xs text-gray-500">
                      Position: ({change.position_x}, {change.position_y})
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-900">{change.description}</p>
                {(change.width !== null || change.height !== null) && (
                  <p className="text-xs text-gray-500 mt-2">
                    Size: {change.width || '?'}px × {change.height || '?'}px
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
