import { useState, FormEvent } from 'react';
import { Zap } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import LightningCanvas from './LightningCanvas';

export default function AuthPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [role, setRole] = useState<'user' | 'admin'>('user');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const { signUp, signIn } = useAuth();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      if (isRegister) {
        if (!fullName.trim()) {
          setError('Please enter your full name');
          setLoading(false);
          return;
        }
        const { error: signUpError } = await signUp(email, password, fullName);
        if (signUpError) {
          const errorMsg = signUpError.message || 'Registration failed';
          setError(errorMsg);
          console.error('Signup error:', signUpError);
        } else {
          // Clear form and show success
          setSuccess('Account created successfully! Redirecting to login...');
          setFullName('');
          setEmail('');
          setPassword('');
          setError('');
          // Auto switch to login after successful signup
          setTimeout(() => {
            setIsRegister(false);
            setSuccess('');
          }, 2000);
        }
      } else {
        const { error: signInError } = await signIn(email, password);
        if (signInError) {
          const errorMsg = signInError.message || 'Login failed. Check your credentials.';
          setError(errorMsg);
          console.error('Signin error:', signInError);
        } else {
          setSuccess('Login successful! Redirecting...');
        }
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'An unexpected error occurred';
      setError(errorMsg);
      console.error('Auth error:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleForm = () => {
    setIsRegister(!isRegister);
    setError('');
    setSuccess('');
    setFullName('');
    setEmail('');
    setPassword('');
  };

  const roleLabel = role.charAt(0).toUpperCase() + role.slice(1);
  const authTitle = `${roleLabel} ${isRegister ? 'Registration' : 'Login'}`;

  return (
    <div className="min-h-screen overflow-hidden">
      <LightningCanvas />

      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen">
        <div className="absolute top-5 right-5 bg-white/5 px-5 py-2.5 rounded-full border border-[#3dcd58] text-sm tracking-wider backdrop-blur-md">
          <span className="inline-block w-2 h-2 bg-[#3dcd58] rounded-full mr-2 animate-pulse"></span>
          Team: <span className="text-[#3dcd58] font-bold">CodeTheCurrent</span>
        </div>

        <div className="bg-[rgba(10,15,20,0.8)] w-[400px] p-10 rounded-3xl border border-white/10 text-center shadow-[0_25px_50px_rgba(0,0,0,0.5)] backdrop-blur-[15px]">
          <div className="mb-6">
            <div className="text-[2rem] text-[#3dcd58] mb-2.5">
              <Zap className="w-8 h-8 mx-auto" />
            </div>
            <h1 className="my-2.5 text-3xl font-extrabold text-[#3dcd58]">
              Schneider Electric
            </h1>
            <p className="text-[0.7rem] text-gray-500 uppercase tracking-[2px]">
              Life Is On | Innovation Summit
            </p>
          </div>

          <div className="flex bg-[#1a1f24] my-6 rounded-xl p-1.5">
            <label
              className={`flex-1 py-2.5 cursor-pointer transition-all rounded-lg text-sm ${role === 'user'
                ? 'bg-[#3dcd58] text-black font-bold'
                : 'text-white'
                }`}
            >
              <input
                type="radio"
                name="role"
                value="user"
                checked={role === 'user'}
                onChange={() => setRole('user')}
                className="hidden"
              />
              User
            </label>
            <label
              className={`flex-1 py-2.5 cursor-pointer transition-all rounded-lg text-sm ${role === 'admin'
                ? 'bg-[#3dcd58] text-black font-bold'
                : 'text-white'
                }`}
            >
              <input
                type="radio"
                name="role"
                value="admin"
                checked={role === 'admin'}
                onChange={() => setRole('admin')}
                className="hidden"
              />
              Admin
            </label>
          </div>

          <div>
            <h2 className="text-xl mb-4 text-white">{authTitle}</h2>
            <form onSubmit={handleSubmit}>
              {isRegister && (
                <div className="mb-2">
                  <input
                    type="text"
                    placeholder="Full Name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    className="w-full p-4 my-2 bg-white/5 border border-white/10 rounded-lg text-white transition-all focus:border-[#3dcd58] focus:bg-white/10 focus:outline-none"
                  />
                </div>
              )}
              <div className="mb-2">
                <input
                  type="email"
                  placeholder="Email Address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full p-4 my-2 bg-white/5 border border-white/10 rounded-lg text-white transition-all focus:border-[#3dcd58] focus:bg-white/10 focus:outline-none"
                />
              </div>
              <div className="mb-2">
                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full p-4 my-2 bg-white/5 border border-white/10 rounded-lg text-white transition-all focus:border-[#3dcd58] focus:bg-white/10 focus:outline-none"
                />
              </div>

              {success && (
                <div className="my-3 p-4 bg-green-500/20 border border-green-500 rounded-lg text-green-200 text-sm font-medium">
                  <div className="flex items-start gap-2">
                    <span className="text-green-400 mt-1">✓</span>
                    <div>{success}</div>
                  </div>
                </div>
              )}

              {error && (
                <div className="my-3 p-4 bg-red-500/20 border border-red-500 rounded-lg text-red-200 text-sm font-medium max-h-24 overflow-y-auto">
                  <div className="flex items-start gap-2">
                    <span className="text-red-400 mt-1">•</span>
                    <div>{error}</div>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full p-4 mt-5 bg-[#3dcd58] border-none rounded-lg font-black cursor-pointer transition-all tracking-wider hover:shadow-[0_0_20px_#3dcd58] hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'PROCESSING...' : isRegister ? 'CREATE ACCOUNT' : 'AUTHENTICATE'}
              </button>
            </form>

            <div className="mt-5 text-sm text-gray-500">
              <span>{isRegister ? 'Already registered?' : 'New to the grid?'}</span>
              <button
                onClick={toggleForm}
                className="text-[#3dcd58] ml-1.5 bg-transparent border-none cursor-pointer hover:underline"
              >
                {isRegister ? 'Login here' : 'Request Access'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
