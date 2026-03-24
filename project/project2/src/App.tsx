import { useEffect } from 'react';
import { useAuth } from './contexts/AuthContext';
import AuthPage from './components/AuthPage';
import Dashboard from './components/Dashboard';

function App() {
  const { user, loading } = useAuth();

  useEffect(() => {
    if (user) {
      window.parent.postMessage({ type: 'AUTH_SUCCESS', email: user.email }, '*');
    }
  }, [user]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#050a0e] flex items-center justify-center">
        <div className="text-[#3dcd58] text-xl">Loading...</div>
      </div>
    );
  }

  return user ? <Dashboard /> : <AuthPage />;
}

export default App;
