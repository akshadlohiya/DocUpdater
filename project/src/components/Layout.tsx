import { ReactNode } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  FileText,
  LayoutDashboard,
  FolderOpen,
  GitCompare,
  FileSearch,
  Users,
  LogOut,
  Menu,
  X
} from 'lucide-react';
import { useState } from 'react';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { profile, signOut } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleSignOut = async () => {
    await signOut();
    navigate('/login');
  };

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, roles: ['admin', 'technical_writer', 'reviewer', 'viewer'] },
    { name: 'Projects', href: '/projects', icon: FolderOpen, roles: ['admin', 'technical_writer', 'reviewer', 'viewer'] },
    { name: 'Comparisons', href: '/comparisons', icon: GitCompare, roles: ['admin', 'technical_writer', 'reviewer', 'viewer'] },
    { name: 'Audit Logs', href: '/audit-logs', icon: FileSearch, roles: ['admin'] },
    { name: 'Users', href: '/users', icon: Users, roles: ['admin'] },
  ];

  const filteredNavigation = navigation.filter(item =>
    profile && item.roles.includes(profile.role)
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <Link to="/dashboard" className="flex items-center">
                <div className="flex items-center">
                  <FileText className="w-8 h-8 text-blue-600" />
                  <span className="ml-2 text-xl font-bold text-gray-900">DocUpdater</span>
                </div>
              </Link>
              <div className="hidden md:ml-10 md:flex md:space-x-8">
                {filteredNavigation.map((item) => {
                  const Icon = item.icon;
                  const isActive = location.pathname.startsWith(item.href);
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? 'border-blue-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      <Icon className="w-4 h-4 mr-2" />
                      {item.name}
                    </Link>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center">
              <div className="hidden md:flex items-center space-x-4">
                <div className="text-sm">
                  <div className="font-medium text-gray-900">{profile?.full_name || profile?.email}</div>
                  <div className="text-gray-500 capitalize">{profile?.role.replace('_', ' ')}</div>
                </div>
                <button
                  onClick={handleSignOut}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Sign Out
                </button>
              </div>

              <div className="md:hidden">
                <button
                  onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                  className="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
                >
                  {mobileMenuOpen ? (
                    <X className="w-6 h-6" />
                  ) : (
                    <Menu className="w-6 h-6" />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="md:hidden border-t border-gray-200">
            <div className="pt-2 pb-3 space-y-1">
              {filteredNavigation.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center px-4 py-2 text-base font-medium ${
                      isActive
                        ? 'bg-blue-50 border-l-4 border-blue-500 text-blue-700'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                  >
                    <Icon className="w-5 h-5 mr-3" />
                    {item.name}
                  </Link>
                );
              })}
            </div>
            <div className="pt-4 pb-3 border-t border-gray-200">
              <div className="px-4 mb-3">
                <div className="font-medium text-gray-900">{profile?.full_name || profile?.email}</div>
                <div className="text-sm text-gray-500 capitalize">{profile?.role.replace('_', ' ')}</div>
              </div>
              <button
                onClick={handleSignOut}
                className="flex items-center w-full px-4 py-2 text-base font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              >
                <LogOut className="w-5 h-5 mr-3" />
                Sign Out
              </button>
            </div>
          </div>
        )}
      </nav>

      <main className="py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {children}
        </div>
      </main>
    </div>
  );
}
