import { Zap, LogOut, User, Shield } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import LightningCanvas from './LightningCanvas';

export default function Dashboard() {
  const { profile, signOut } = useAuth();

  if (!profile) return null;

  const isAdmin = profile.role === 'admin';

  return (
    <div className="min-h-screen overflow-hidden">
      <LightningCanvas />

      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen">
        <div className="absolute top-5 right-5 bg-white/5 px-5 py-2.5 rounded-full border border-[#3dcd58] text-sm tracking-wider backdrop-blur-md">
          <span className="inline-block w-2 h-2 bg-[#3dcd58] rounded-full mr-2 animate-pulse"></span>
          Team: <span className="text-[#3dcd58] font-bold">CodeTheCurrent</span>
        </div>

        <div className="bg-[rgba(10,15,20,0.8)] w-[500px] p-10 rounded-3xl border border-white/10 shadow-[0_25px_50px_rgba(0,0,0,0.5)] backdrop-blur-[15px]">
          <div className="text-center mb-8">
            <div className="text-[2rem] text-[#3dcd58] mb-2.5">
              <Zap className="w-12 h-12 mx-auto" />
            </div>
            <h1 className="my-2.5 text-3xl font-light">
              Schneider <span className="text-[#3dcd58] font-extrabold">Electric</span>
            </h1>
            <p className="text-[0.7rem] text-gray-500 uppercase tracking-[2px]">
              Life Is On | Innovation Summit
            </p>
          </div>

          <div className="bg-[#3dcd58]/10 border-2 border-[#3dcd58] rounded-2xl p-8 mb-6">
            <div className="flex items-center justify-center mb-6">
              {isAdmin ? (
                <Shield className="w-16 h-16 text-[#3dcd58]" />
              ) : (
                <User className="w-16 h-16 text-[#3dcd58]" />
              )}
            </div>

            <div className="text-center">
              <h2 className="text-2xl font-bold text-[#3dcd58] mb-2">
                Login Successful!
              </h2>
              <p className="text-white/80 mb-4">
                Welcome to the Innovation Summit
              </p>

              <div className="bg-white/5 rounded-xl p-4 mb-4 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400 text-sm">Name:</span>
                  <span className="text-white font-medium">{profile.full_name}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400 text-sm">Email:</span>
                  <span className="text-white font-medium text-sm">{profile.email}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400 text-sm">Role:</span>
                  <span
                    className={`font-bold uppercase text-sm px-3 py-1 rounded-full ${
                      isAdmin
                        ? 'bg-[#3dcd58]/20 text-[#3dcd58]'
                        : 'bg-blue-500/20 text-blue-400'
                    }`}
                  >
                    {profile.role}
                  </span>
                </div>
              </div>

              {isAdmin && (
                <div className="bg-[#3dcd58]/20 border border-[#3dcd58]/50 rounded-lg p-3 mb-4">
                  <p className="text-[#3dcd58] text-sm font-medium">
                    Administrator Access Granted
                  </p>
                </div>
              )}

              <p className="text-gray-400 text-xs">
                Authenticated at {new Date().toLocaleString()}
              </p>
            </div>
          </div>

          <button
            onClick={() => signOut()}
            className="w-full p-4 bg-white/5 border border-white/20 rounded-lg font-bold cursor-pointer transition-all tracking-wider hover:bg-white/10 hover:border-[#3dcd58] flex items-center justify-center gap-2"
          >
            <LogOut className="w-5 h-5" />
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}
