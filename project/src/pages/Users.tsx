import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { logAudit } from '../utils/audit';
import { Search, Users as UsersIcon, Shield, Edit, AlertCircle } from 'lucide-react';
import type { Database, UserRole } from '../lib/database.types';

type UserProfile = Database['public']['Tables']['user_profiles']['Row'];

export function Users() {
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingUser, setEditingUser] = useState<UserProfile | null>(null);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const { data, error } = await supabase
        .from('user_profiles')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) throw error;
      setUsers(data || []);
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredUsers = users.filter(
    (user) =>
      user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (user.full_name && user.full_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const getRoleBadge = (role: UserRole) => {
    const roleConfig = {
      admin: { bg: 'bg-red-100', text: 'text-red-700' },
      technical_writer: { bg: 'bg-blue-100', text: 'text-blue-700' },
      reviewer: { bg: 'bg-green-100', text: 'text-green-700' },
      viewer: { bg: 'bg-gray-100', text: 'text-gray-700' },
    };

    const config = roleConfig[role];

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        <Shield className="w-3 h-3 mr-1" />
        {role.replace('_', ' ')}
      </span>
    );
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
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
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">User Management</h1>
        <p className="mt-2 text-gray-600">
          Manage user accounts and role assignments
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search users by name or email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {filteredUsers.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <UsersIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No users found</h3>
          <p className="text-gray-600">
            {searchTerm ? 'Try adjusting your search terms' : 'No users have registered yet'}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Joined
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {user.full_name || 'Unknown User'}
                        </div>
                        <div className="text-sm text-gray-500">{user.email}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getRoleBadge(user.role)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {formatDate(user.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button
                        onClick={() => setEditingUser(user)}
                        className="inline-flex items-center text-blue-600 hover:text-blue-700"
                      >
                        <Edit className="w-4 h-4 mr-1" />
                        Edit Role
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {editingUser && (
        <EditRoleModal
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onSuccess={() => {
            setEditingUser(null);
            fetchUsers();
          }}
        />
      )}
    </div>
  );
}

interface EditRoleModalProps {
  user: UserProfile;
  onClose: () => void;
  onSuccess: () => void;
}

function EditRoleModal({ user, onClose, onSuccess }: EditRoleModalProps) {
  const [role, setRole] = useState<UserRole>(user.role);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const { error: updateError } = await supabase
        .from('user_profiles')
        .update({ role })
        .eq('id', user.id);

      if (updateError) throw updateError;

      await logAudit('update_user_role', 'user_profile', user.id, {
        old_role: user.role,
        new_role: role,
        email: user.email,
      });

      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update user role');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Edit User Role</h2>
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
              User
            </label>
            <div className="text-sm text-gray-900">
              <div className="font-medium">{user.full_name || 'Unknown User'}</div>
              <div className="text-gray-500">{user.email}</div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Role *
            </label>
            <select
              required
              value={role}
              onChange={(e) => setRole(e.target.value as UserRole)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="viewer">Viewer - Read-only access</option>
              <option value="reviewer">Reviewer - Can approve changes</option>
              <option value="technical_writer">Technical Writer - Can create and edit projects</option>
              <option value="admin">Admin - Full system access</option>
            </select>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-900 mb-2">Role Permissions</h4>
            <ul className="text-xs text-blue-800 space-y-1">
              {role === 'admin' && (
                <>
                  <li>• Full access to all features</li>
                  <li>• Manage users and roles</li>
                  <li>• View audit logs</li>
                  <li>• Create, edit, and delete projects</li>
                </>
              )}
              {role === 'technical_writer' && (
                <>
                  <li>• Create and edit projects</li>
                  <li>• Start documentation runs</li>
                  <li>• Approve changes</li>
                  <li>• View all comparisons</li>
                </>
              )}
              {role === 'reviewer' && (
                <>
                  <li>• View all projects and runs</li>
                  <li>• Review and approve changes</li>
                  <li>• View comparisons</li>
                </>
              )}
              {role === 'viewer' && (
                <>
                  <li>• View projects and runs</li>
                  <li>• View comparisons</li>
                  <li>• Read-only access</li>
                </>
              )}
            </ul>
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
              {loading ? 'Updating...' : 'Update Role'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
