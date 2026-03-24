import { Zap, LogOut, Shield, Plus, Book, FileText, FolderOpen, Download, Calendar, Package, HelpCircle, X } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useState, useEffect, useRef } from 'react';
import { supabase } from '../lib/supabase';

interface LibraryEntry {
  id: number;
  app_name: string;
  version: string;
  pdf_path: string;
  markdown_path: string;
  created_at: string;
  updated_at: string;
}

export default function Dashboard() {
  const { profile, user, signOut } = useAuth();
  const [activeView, setActiveView] = useState('library'); // Default to library for all users
  const [apiKey, setApiKey] = useState('');
  const [appPath, setAppPath] = useState('');
  const [appName, setAppName] = useState('');
  const [outputPath, setOutputPath] = useState('documentation');
  const [version, setVersion] = useState('v1.0');
  const [isInstaller, setIsInstaller] = useState(false);
  const [status, setStatus] = useState('SYSTEM READY');
  const [pdfFile1, setPdfFile1] = useState<File | null>(null);
  const [pdfFile2, setPdfFile2] = useState<File | null>(null);
  const [comparisonResult, setComparisonResult] = useState<string>('');
  const [comparisonData, setComparisonData] = useState<any>(null);
  const [threshold, setThreshold] = useState<number>(0.3);
  const [forceCompare, setForceCompare] = useState<boolean>(false);
  const [libraryEntries, setLibraryEntries] = useState<LibraryEntry[]>([]);
  const [loadingLibrary, setLoadingLibrary] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Show loading while profile is being fetched
  if (!user) return null;
  if (!profile) {
    return (
      <div className="min-h-screen bg-[#050a0e] flex items-center justify-center">
        <div className="text-[#3dcd58] text-xl">Loading profile...</div>
      </div>
    );
  }

  // Temporarily force admin access to bypass Supabase RLS issue
  const isAdmin = true; // profile.role === 'admin';

  // Get authentication token for API calls
  const getAuthToken = async () => {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token || '';
  };

  // Fetch library entries
  const fetchLibrary = async () => {
    setLoadingLibrary(true);
    try {
      const token = await getAuthToken();
      const response = await fetch('http://localhost:8001/api/library', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-User-Role': profile.role
        }
      });

      if (response.ok) {
        const data = await response.json();
        setLibraryEntries(data.library || []);
      } else {
        console.error('Failed to load library');
      }
    } catch (error) {
      console.error('Error fetching library:', error);
    } finally {
      setLoadingLibrary(false);
    }
  };

  // Download PDF from library
  const handleDownload = async (docId: number, appName: string, version: string) => {
    try {
      const token = await getAuthToken();
      const response = await fetch(`http://localhost:8001/api/download/${docId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-User-Role': profile.role
        }
      });

      if (!response.ok) {
        console.error('Failed to download PDF');
        return;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${appName}_${version}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download error:', error);
    }
  };

  // Connect to WebSocket
  useEffect(() => {
    // Use current window location to support network access
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const wsUrl = `${protocol}//${host}:8001/ws`;

    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setStatus('SYSTEM READY');
      };

      wsRef.current.onmessage = (event) => {
        console.log(event.data);
      };

      wsRef.current.onclose = () => {
        setStatus('DISCONNECTED');
      };

      wsRef.current.onerror = () => {
        setStatus('ERROR');
      };
    } catch (err) {
      console.error('WebSocket error:', err);
      setStatus('ERROR');
    }

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Load library when switching to library view
  useEffect(() => {
    if (activeView === 'library') {
      fetchLibrary();
    }
  }, [activeView]);

  // ESC key to close help modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showHelp) {
        setShowHelp(false);
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [showHelp]);

  const handleGenerate = () => {
    if (!apiKey || !appPath || !appName) {
      console.log('❌ Please fill in required fields');
      return;
    }

    const payload = {
      api_key: apiKey,
      app_path: appPath,
      app_name: appName,
      output_path: outputPath,
      version: version,
      is_installer: isInstaller,
      max_depth: 2,
      max_screenshots: 30
    };

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
      setStatus('GENERATING...');
      console.log(`🚀 Starting documentation generation for ${appName}...`);
    } else {
      console.log('❌ Server connection lost');
    }
  };

  const handleComparePDFs = async () => {
    if (!pdfFile1 || !pdfFile2) {
      setComparisonResult('Please upload both PDF files');
      return;
    }

    try {
      setComparisonResult('🔄 Comparing PDFs... This may take a moment.');

      const token = await getAuthToken();
      const formData = new FormData();
      formData.append('pdf1', pdfFile1);
      formData.append('pdf2', pdfFile2);
      formData.append('threshold', threshold.toString());
      formData.append('force_compare', forceCompare.toString());

      const response = await fetch('http://localhost:8001/api/compare-pdfs', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-User-Role': profile.role
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        setComparisonResult(`❌ Error: ${errorData.message || errorData.detail || 'Comparison failed'}`);
        return;
      }

      // Get the ZIP file blob and force download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'pdf_comparison_results.zip';  // Force ZIP download
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      setComparisonResult(
        `✓ Comparison Complete!\n\n` +
        `ZIP file downloaded: pdf_comparison_results.zip\n\n` +
        `Extract the ZIP to find:\n` +
        `• comparison_visual.pdf - Visual overlay\n` +
        `• comparison_log.pdf - Detailed change log\n\n` +
        `Comparison methodology used\n` +
        `• Processing status and file information`
      );

      setPdfFile1(null);
      setPdfFile2(null);
      setForceCompare(false);
    } catch (error) {
      setComparisonResult(`❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  /* Native Picker Implementation */
  const handleNativePick = async (mode: 'file' | 'directory', currentPath: string = '') => {
    try {
      const response = await fetch('http://localhost:8001/api/pick-native', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode, path: currentPath }),
      });

      const data = await response.json();
      if (data.success && data.path) {
        return data.path;
      }
    } catch (error) {
      console.error('Picker error:', error);
    }
    return null;
  };

  const pickAppExecutable = async () => {
    const path = await handleNativePick('file', appPath);
    if (path) setAppPath(path);
  };

  const pickOutputDirectory = async () => {
    const path = await handleNativePick('directory', outputPath);
    if (path) setOutputPath(path);
  };

  const handleOpenFolder = async (path: string) => {
    if (!path) return;
    try {
      const response = await fetch('http://localhost:8001/api/open-folder', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path }),
      });

      const data = await response.json();
      if (!data.success) {
        console.error(`Failed to open folder: ${data.message}`);
      }
    } catch (error) {
      console.error('Error opening folder:', error);
    }
  };

  return (
    <div className="min-h-screen bg-[#0b0e14]">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/50 backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 py-6 flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400">
              GUI Agent v2.1
            </h1>
            <p className="text-gray-400 text-sm mt-1">Automated Documentation Engine</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-gray-400">User:</span>
              <span className="text-white font-medium">{profile.full_name}</span>
              {isAdmin && (
                <span className="flex items-center gap-1 px-2 py-1 bg-purple-500/20 text-purple-400 rounded text-xs font-semibold border border-purple-500/30">
                  <Shield className="w-3 h-3" /> ADMIN (BYPASS)
                </span>
              )}
              {!isAdmin && (
                <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs font-semibold border border-blue-500/30">
                  USER
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-black/40 border border-gray-700/50 rounded-lg">
              <div className={`h-2 w-2 rounded-full animate-pulse ${status === 'SYSTEM READY' ? 'bg-emerald-500' : status === 'DISCONNECTED' ? 'bg-red-500' : 'bg-yellow-500'}`}></div>
              <span className={`text-xs font-semibold ${status === 'SYSTEM READY' ? 'text-emerald-400' : status === 'DISCONNECTED' ? 'text-red-400' : 'text-yellow-400'}`}>
                {status === 'SYSTEM READY' ? 'Server Connected' : status === 'DISCONNECTED' ? 'Server Offline' : 'Server Connecting...'}
              </span>
            </div>
            <button
              onClick={() => setShowHelp(true)}
              className="px-4 py-2 bg-blue-600/20 hover:bg-blue-600/30 rounded-lg text-blue-400 hover:text-blue-300 transition flex items-center gap-2"
              title="Help & Guide"
            >
              <HelpCircle className="w-4 h-4" /> Help
            </button>
            <button
              onClick={() => signOut()}
              className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-gray-300 hover:text-white transition flex items-center gap-2"
            >
              <LogOut className="w-4 h-4" /> Sign Out
            </button>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex gap-2 px-6 pb-4 border-t border-gray-800">
          {isAdmin && (
            <button
              onClick={() => setActiveView('generator')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${activeView === 'generator'
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/20'
                : 'text-gray-400 hover:text-white'
                }`}
            >
              <Plus className="w-4 h-4" /> Generate
            </button>
          )}
          <button
            onClick={() => setActiveView('library')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${activeView === 'library'
              ? 'bg-blue-500/20 text-blue-400 border border-blue-500/20'
              : 'text-gray-400 hover:text-white'
              }`}
          >
            <Book className="w-4 h-4" /> Library
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {activeView === 'generator' && isAdmin && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Configuration Panel */}
            <div className="space-y-4 bg-gradient-to-br from-gray-900/80 to-black p-6 rounded-2xl border border-gray-700/50 shadow-2xl">
              <h2 className="text-lg font-bold text-white">Configuration</h2>

              <div>
                <label className="text-xs font-bold text-gray-400 uppercase">API Key</label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter Gemini API key"
                  title="Get your API key from Google AI Studio (makersuite.google.com/app/apikey)"
                  className="w-full bg-black border border-gray-700 text-white rounded-lg p-3 mt-1 focus:border-blue-500 outline-none transition"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-gray-400 uppercase">App Path</label>
                <div className="flex gap-2 mt-1">
                  <input
                    type="text"
                    value={appPath}
                    onChange={(e) => setAppPath(e.target.value)}
                    placeholder="C:/Program Files/..."
                    className="flex-1 bg-black border border-gray-700 text-white rounded-lg p-3 focus:border-blue-500 outline-none transition"
                  />
                  <button
                    onClick={pickAppExecutable}
                    className="px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition text-sm font-semibold"
                    title="Pick Executable"
                  >
                    📁
                  </button>
                  <button
                    onClick={() => handleOpenFolder(appPath.replace(/[^\\/]*$/, ''))}
                    className="px-4 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition text-sm font-semibold"
                    title="Open Folder"
                  >
                    <FolderOpen className="w-5 h-5" />
                  </button>
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-gray-400 uppercase">App Name</label>
                <input
                  type="text"
                  value={appName}
                  onChange={(e) => setAppName(e.target.value)}
                  placeholder="My App"
                  title="Enter a friendly name for the application being documented"
                  className="w-full bg-black border border-gray-700 text-white rounded-lg p-3 mt-1 focus:border-blue-500 outline-none transition"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-gray-400 uppercase">Output Directory</label>
                <div className="flex gap-2 mt-1">
                  <input
                    type="text"
                    value={outputPath}
                    onChange={(e) => setOutputPath(e.target.value)}
                    placeholder="documentation"
                    className="flex-1 bg-black border border-gray-700 text-white rounded-lg p-3 focus:border-blue-500 outline-none transition"
                  />
                  <button
                    onClick={pickOutputDirectory}
                    className="px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition text-sm font-semibold"
                    title="Pick Directory"
                  >
                    📁
                  </button>
                  <button
                    onClick={() => handleOpenFolder(outputPath)}
                    className="px-4 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition text-sm font-semibold"
                    title="Open Folder"
                  >
                    <FolderOpen className="w-5 h-5" />
                  </button>
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-gray-400 uppercase">Version</label>
                <input
                  type="text"
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  placeholder="v1.0"
                  title="Specify version number (e.g., v1.0, v2.1)"
                  className="w-full bg-black border border-gray-700 text-white rounded-lg p-3 mt-1 focus:border-blue-500 outline-none transition"
                />
              </div>

              <div className="flex items-center gap-3 bg-black/40 p-3 rounded-lg border border-gray-700/50">
                <input
                  type="checkbox"
                  id="isInstaller"
                  checked={isInstaller}
                  onChange={(e) => setIsInstaller(e.target.checked)}
                  className="w-5 h-5 accent-blue-500 rounded cursor-pointer"
                />
                <label htmlFor="isInstaller" className="text-sm font-medium text-gray-300 cursor-pointer select-none">
                  Installation Guide Mode
                  <span className="block text-xs text-gray-500 font-normal">
                    Generates step-by-step installation walkthrough
                  </span>
                </label>
              </div>

              <button
                onClick={handleGenerate}
                className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-bold py-4 rounded-xl transition active:scale-95 shadow-lg"
              >
                <Zap className="w-5 h-5 inline mr-2" /> RUN WITH ADMIN
              </button>
            </div>

            {/* PDF Comparison Panel */}
            <div className="lg:col-span-2">
              <div className="bg-gradient-to-br from-gray-900/80 to-black rounded-2xl border border-gray-700/50 overflow-hidden flex flex-col h-[600px] shadow-2xl">
                <div className="bg-gradient-to-r from-cyan-900/40 to-blue-900/40 px-6 py-4 border-b border-cyan-500/20 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-white">PDF Comparison</h3>
                    <p className="text-xs text-gray-300 mt-1">Compare document versions side by side</p>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                  {/* File Upload Section */}
                  <div className="grid grid-cols-2 gap-4">
                    {/* PDF 1 Upload */}
                    <div className="bg-black/40 rounded-xl border border-dashed border-cyan-500/30 p-4 hover:border-cyan-500/60 transition cursor-pointer group">
                      <label className="cursor-pointer block text-center">
                        <div className="w-12 h-12 rounded-lg bg-cyan-500/10 flex items-center justify-center mx-auto mb-2 group-hover:bg-cyan-500/20 transition">
                          <FileText className="w-6 h-6 text-cyan-400" />
                        </div>
                        <p className="text-xs font-semibold text-gray-300 mb-1">
                          {pdfFile1 ? pdfFile1.name : 'Upload PDF 1'}
                        </p>
                        <p className="text-xs text-gray-500">Click to select file</p>
                        <input
                          type="file"
                          accept=".pdf"
                          onChange={(e) => setPdfFile1(e.target.files?.[0] || null)}
                          className="hidden"
                        />
                      </label>
                    </div>

                    {/* PDF 2 Upload */}
                    <div className="bg-black/40 rounded-xl border border-dashed border-emerald-500/30 p-4 hover:border-emerald-500/60 transition cursor-pointer group">
                      <label className="cursor-pointer block text-center">
                        <div className="w-12 h-12 rounded-lg bg-emerald-500/10 flex items-center justify-center mx-auto mb-2 group-hover:bg-emerald-500/20 transition">
                          <FileText className="w-6 h-6 text-emerald-400" />
                        </div>
                        <p className="text-xs font-semibold text-gray-300 mb-1">
                          {pdfFile2 ? pdfFile2.name : 'Upload PDF 2'}
                        </p>
                        <p className="text-xs text-gray-500">Click to select file</p>
                        <input
                          type="file"
                          accept=".pdf"
                          onChange={(e) => setPdfFile2(e.target.files?.[0] || null)}
                          className="hidden"
                        />
                      </label>
                    </div>
                  </div>

                  {/* Threshold Slider */}
                  {pdfFile1 && pdfFile2 && (
                    <div className="bg-black/40 rounded-xl border border-gray-700/50 p-4">
                      <label className="text-xs font-bold text-gray-400 uppercase mb-2 block">Similarity Threshold</label>
                      <div className="flex items-center gap-4">
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={threshold}
                          onChange={(e) => setThreshold(parseFloat(e.target.value))}
                          className="flex-1 accent-cyan-500"
                        />
                        <span className="text-sm font-semibold text-white bg-cyan-500/20 px-3 py-1 rounded-lg border border-cyan-500/30 min-w-[60px] text-center">
                          {(threshold * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-2">
                        {threshold < 0.3 ? '⚠️ Low threshold - may compare unrelated documents' : threshold > 0.7 ? '🔒 High threshold - only very similar documents accepted' : '✓ Recommended for version comparison'}
                      </p>
                    </div>
                  )}

                  {/* Force Compare Checkbox */}
                  {pdfFile1 && pdfFile2 && (
                    <div className="bg-black/40 rounded-xl border border-gray-700/50 p-4">
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          id="forceCompare"
                          checked={forceCompare}
                          onChange={(e) => setForceCompare(e.target.checked)}
                          className="w-5 h-5 accent-orange-500 rounded cursor-pointer mt-0.5"
                        />
                        <label htmlFor="forceCompare" className="flex-1 cursor-pointer select-none">
                          <div className="text-sm font-semibold text-gray-300">
                            Skip validation (force compare)
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            Use this when comparing major version changes with significant content differences
                          </p>
                          {forceCompare && (
                            <div className="mt-2 px-3 py-2 bg-orange-500/10 border border-orange-500/30 rounded-lg">
                              <p className="text-xs text-orange-400">
                                ⚠️ Validation bypassed - comparison will proceed regardless of document similarity
                              </p>
                            </div>
                          )}
                        </label>
                      </div>
                    </div>
                  )}

                  {/* Compare Button */}
                  {pdfFile1 && pdfFile2 && (
                    <button
                      onClick={handleComparePDFs}
                      className="w-full bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-500 hover:to-emerald-500 text-white font-semibold py-2 rounded-lg transition active:scale-95 shadow-lg shadow-cyan-500/20">
                      Compare PDFs
                    </button>
                  )}

                  {/* Results Area */}
                  {comparisonResult ? (
                    <div className="space-y-3">
                      <div className="bg-black/40 rounded-xl border border-gray-700/50 p-4">
                        <p className="text-xs font-bold text-emerald-400 mb-2">✓ Comparison Complete</p>
                        <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">{comparisonResult}</p>
                      </div>

                      {comparisonData && (
                        <button
                          onClick={() => {
                            setComparisonResult('');
                            setPdfFile1(null);
                            setPdfFile2(null);
                            setComparisonData(null);
                            setForceCompare(false);
                          }}
                          className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold py-2 rounded-lg transition active:scale-95 text-sm">
                          🔄 Compare Another
                        </button>
                      )}
                    </div>
                  ) : (
                    <div className="flex-1 flex items-center justify-center text-center">
                      <div>
                        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-cyan-500/10 to-emerald-500/10 flex items-center justify-center mx-auto mb-3">
                          <FileText className="w-8 h-8 text-gray-600" />
                        </div>
                        <p className="text-sm text-gray-400">Upload two PDFs to compare</p>
                        <p className="text-xs text-gray-500 mt-2">Analyze differences, generate detailed reports</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeView === 'library' && (
          <div className="bg-gradient-to-br from-gray-900/80 to-black p-6 rounded-2xl border border-gray-700/50 shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold text-white">Documentation Library</h2>
                <p className="text-sm text-gray-400 mt-1">Download generated documentation PDFs</p>
              </div>
              <button
                onClick={fetchLibrary}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition flex items-center gap-2"
              >
                🔄 Refresh
              </button>
            </div>

            {loadingLibrary ? (
              <div className="text-center py-20">
                <div className="w-16 h-16 rounded-full bg-blue-500/10 flex items-center justify-center mx-auto mb-4 animate-pulse">
                  <Book className="w-8 h-8 text-blue-400" />
                </div>
                <p className="text-gray-400">Loading library...</p>
              </div>
            ) : libraryEntries.length === 0 ? (
              <div className="text-center py-20">
                <Book className="w-20 h-20 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400 text-lg">No documentation available yet</p>
                <p className="text-gray-500 text-sm mt-2">
                  {isAdmin ? 'Generate documentation above to see it here' : 'Ask an admin to generate documentation'}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {libraryEntries.map((entry) => (
                  <div
                    key={entry.id}
                    className="bg-black/40 rounded-xl border border-gray-700/50 p-5 hover:border-blue-500/30 transition group"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500/20 to-emerald-500/20 flex items-center justify-center">
                          <FileText className="w-5 h-5 text-blue-400" />
                        </div>
                        <div>
                          <h3 className="text-sm font-bold text-white group-hover:text-blue-400 transition">
                            {entry.app_name}
                          </h3>
                          <div className="flex items-center gap-1 mt-1">
                            <Package className="w-3 h-3 text-gray-500" />
                            <span className="text-xs text-gray-500">{entry.version}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-gray-500 mb-4">
                      <Calendar className="w-3 h-3" />
                      <span>{new Date(entry.created_at).toLocaleDateString()}</span>
                    </div>

                    <button
                      onClick={() => handleDownload(entry.id, entry.app_name, entry.version)}
                      className="w-full bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white font-semibold py-2 rounded-lg transition active:scale-95 flex items-center justify-center gap-2"
                    >
                      <Download className="w-4 h-4" />
                      Download PDF
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Help Modal */}
      {showHelp && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setShowHelp(false)}
        >
          <div
            className="bg-gradient-to-br from-gray-900 to-black border border-gray-700 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="sticky top-0 bg-gradient-to-r from-blue-900/40 to-emerald-900/40 border-b border-gray-700 px-6 py-4 flex items-center justify-between backdrop-blur">
              <div>
                <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                  <HelpCircle className="w-6 h-6 text-blue-400" />
                  Help & User Guide
                </h2>
                <p className="text-sm text-gray-400 mt-1">Learn how to use GUI Agent v2.1</p>
              </div>
              <button
                onClick={() => setShowHelp(false)}
                className="p-2 hover:bg-white/10 rounded-lg transition"
                title="Close (ESC)"
              >
                <X className="w-6 h-6 text-gray-400" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
              {/* Overview */}
              <section className="bg-black/40 rounded-xl border border-blue-500/30 p-5">
                <h3 className="text-xl font-bold text-blue-400 mb-3">📘 Application Overview</h3>
                <p className="text-gray-300 leading-relaxed">
                  <strong className="text-white">GUI Agent v2.1</strong> is an automated documentation engine that generates comprehensive user manuals
                  by exploring applications through their user interface. It can also compare different versions of PDF documents
                  to identify changes.
                </p>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="bg-blue-500/10 rounded-lg p-3 border border-blue-500/20">
                    <div className="text-blue-400 font-semibold text-sm mb-1">👨‍💼 Admin Users</div>
                    <div className="text-xs text-gray-400">Generate documentation, compare PDFs, access library</div>
                  </div>
                  <div className="bg-emerald-500/10 rounded-lg p-3 border border-emerald-500/20">
                    <div className="text-emerald-400 font-semibold text-sm mb-1">👤 Regular Users</div>
                    <div className="text-xs text-gray-400">Browse and download documentation from library</div>
                  </div>
                </div>
              </section>

              {/* Documentation Generation Guide - Admin Only */}
              {isAdmin && (
                <section className="bg-black/40 rounded-xl border border-emerald-500/30 p-5">
                  <h3 className="text-xl font-bold text-emerald-400 mb-3">⚡ Documentation Generation Guide</h3>
                  <p className="text-gray-300 text-sm mb-4">
                    Follow these steps to generate automated documentation for any application:
                  </p>

                  <div className="space-y-3">
                    {/* Step 1 */}
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-sm">
                        1
                      </div>
                      <div className="flex-1">
                        <div className="text-white font-semibold text-sm mb-1">🔑 Enter Gemini API Key</div>
                        <div className="text-gray-400 text-xs">
                          Paste your Google Gemini API key for AI-powered documentation generation. Get one from
                          <a href="https://makersuite.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline ml-1">Google AI Studio</a>
                        </div>
                      </div>
                    </div>

                    {/* Step 2 */}
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-sm">
                        2
                      </div>
                      <div className="flex-1">
                        <div className="text-white font-semibold text-sm mb-1">📁 Select Application Path</div>
                        <div className="text-gray-400 text-xs">
                          Click the folder icon 📁 to browse and select the executable file (.exe) of the application you want to document.
                          You can also type the path manually.
                        </div>
                      </div>
                    </div>

                    {/* Step 3 */}
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-sm">
                        3
                      </div>
                      <div className="flex-1">
                        <div className="text-white font-semibold text-sm mb-1">✏️ Enter Application Name</div>
                        <div className="text-gray-400 text-xs">
                          Provide a friendly name for the application (e.g., "Adobe Reader", "Calculator"). This will be used in the documentation.
                        </div>
                      </div>
                    </div>

                    {/* Step 4 */}
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-sm">
                        4
                      </div>
                      <div className="flex-1">
                        <div className="text-white font-semibold text-sm mb-1">📂 Choose Output Directory</div>
                        <div className="text-gray-400 text-xs">
                          Select where the generated documentation will be saved. Default is the "documentation" folder.
                          Click 📁 to browse or type a custom path.
                        </div>
                      </div>
                    </div>

                    {/* Step 5 */}
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-sm">
                        5
                      </div>
                      <div className="flex-1">
                        <div className="text-white font-semibold text-sm mb-1">🏷️ Set Version Number</div>
                        <div className="text-gray-400 text-xs">
                          Specify the version (e.g., v1.0, v2.1). The system auto-detects existing versions and suggests the next version.
                        </div>
                      </div>
                    </div>

                    {/* Step 6 */}
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-sm">
                        6
                      </div>
                      <div className="flex-1">
                        <div className="text-white font-semibold text-sm mb-1">🎯 Installation Guide Mode (Optional)</div>
                        <div className="text-gray-400 text-xs">
                          Check this box if you want to generate step-by-step installation instructions instead of a regular user manual.
                        </div>
                      </div>
                    </div>

                    {/* Step 7 */}
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-sm">
                        7
                      </div>
                      <div className="flex-1">
                        <div className="text-white font-semibold text-sm mb-1">⚡ Click "RUN WITH ADMIN"</div>
                        <div className="text-gray-400 text-xs">
                          Start the documentation generation process. The agent will explore the application, take screenshots,
                          and generate a comprehensive PDF manual. This process may take several minutes depending on the application size.
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3">
                    <div className="text-yellow-400 text-xs font-semibold mb-1">⚠️ Important Notes:</div>
                    <ul className="text-gray-400 text-xs space-y-1 list-disc list-inside">
                      <li>Ensure the application can run without errors</li>
                      <li>Close any instances of the application before starting</li>
                      <li>The process requires active screen interaction - do not minimize the window</li>
                      <li>Generated documentation appears in the Library tab when complete</li>
                    </ul>
                  </div>
                </section>
              )}

              {/* PDF Comparison Guide - Admin Only */}
              {isAdmin && (
                <section className="bg-black/40 rounded-xl border border-cyan-500/30 p-5">
                  <h3 className="text-xl font-bold text-cyan-400 mb-3">⚖️ PDF Comparison Guide</h3>
                  <p className="text-gray-300 text-sm mb-4">
                    Compare two PDF documents to identify changes, additions, and deletions:
                  </p>

                  <div className="space-y-3">
                    {/* Step 1 */}
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold text-sm">
                        1
                      </div>
                      <div className="flex-1">
                        <div className="text-white font-semibold text-sm mb-1">📄 Upload First PDF (Old Version)</div>
                        <div className="text-gray-400 text-xs">
                          Click on the first upload box and select the original/older version of your PDF document.
                        </div>
                      </div>
                    </div>

                    {/* Step 2 */}
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold text-sm">
                        2
                      </div>
                      <div className="flex-1">
                        <div className="text-white font-semibold text-sm mb-1">📄 Upload Second PDF (New Version)</div>
                        <div className="text-gray-400 text-xs">
                          Click on the second upload box and select the updated/newer version of your PDF document.
                        </div>
                      </div>
                    </div>

                    {/* Step 3 */}
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold text-sm">
                        3
                      </div>
                      <div className="flex-1">
                        <div className="text-white font-semibold text-sm mb-1">🎚️ Adjust Similarity Threshold</div>
                        <div className="text-gray-400 text-xs">
                          Use the slider to set how similar the documents should be (0-100%). Recommended: 20-40% for version comparisons.
                        </div>
                        <div className="mt-2 bg-gray-900/50 rounded p-2 text-xs text-gray-400">
                          <div className="flex justify-between mb-1">
                            <span>Low (0-30%)</span>
                            <span>Medium (30-70%)</span>
                            <span>High (70-100%)</span>
                          </div>
                          <div className="flex justify-between text-[10px] text-gray-500">
                            <span>⚠️ May compare unrelated</span>
                            <span>✅ Recommended</span>
                            <span>🔒 Only very similar</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Step 4 */}
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold text-sm">
                        4
                      </div>
                      <div className="flex-1">
                        <div className="text-white font-semibold text-sm mb-1">⚡ Click "Compare PDFs"</div>
                        <div className="text-gray-400 text-xs">
                          Start the comparison process. This may take a few moments depending on the PDF size and complexity.
                        </div>
                      </div>
                    </div>

                    {/* Step 5 */}
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold text-sm">
                        5
                      </div>
                      <div className="flex-1">
                        <div className="text-white font-semibold text-sm mb-1">📥 Download Results ZIP</div>
                        <div className="text-gray-400 text-xs">
                          The system generates a ZIP file containing:
                          <ul className="list-disc list-inside mt-1 ml-2 space-y-0.5">
                            <li><strong className="text-white">comparison_visual.pdf</strong> - Side-by-side visual overlay</li>
                            <li><strong className="text-white">comparison_log.pdf</strong> - Detailed change log</li>
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
                    <div className="text-blue-400 text-xs font-semibold mb-1">💡 Pro Tips:</div>
                    <ul className="text-gray-400 text-xs space-y-1 list-disc list-inside">
                      <li>For detecting minor changes, use a higher threshold (60-80%)</li>
                      <li>For comparing different versions, use medium threshold (30-50%)</li>
                      <li>If comparison fails, the documents may be completely different - check similarity threshold</li>
                    </ul>
                  </div>
                </section>
              )}

              {/* Library Guide - All Users */}
              <section className="bg-black/40 rounded-xl border border-blue-500/30 p-5">
                <h3 className="text-xl font-bold text-blue-400 mb-3">📚 Documentation Library</h3>
                <p className="text-gray-300 text-sm mb-4">
                  Browse and download all generated documentation:
                </p>

                <div className="space-y-3">
                  <div className="flex gap-3">
                    <div className="text-2xl">📖</div>
                    <div className="flex-1">
                      <div className="text-white font-semibold text-sm mb-1">Browse Documentation</div>
                      <div className="text-gray-400 text-xs">
                        Click the <strong className="text-blue-400">"Library"</strong> tab in the navigation to view all available documentation.
                        Each entry shows the application name, version, and creation date.
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <div className="text-2xl">📥</div>
                    <div className="flex-1">
                      <div className="text-white font-semibold text-sm mb-1">Download PDF</div>
                      <div className="text-gray-400 text-xs">
                        Click <strong className="text-emerald-400">"Download PDF"</strong> on any library entry to save the documentation file to your computer.
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <div className="text-2xl">🔄</div>
                    <div className="flex-1">
                      <div className="text-white font-semibold text-sm mb-1">Refresh Library</div>
                      <div className="text-gray-400 text-xs">
                        Click the <strong className="text-blue-400">"🔄 Refresh"</strong> button to check for newly generated documentation.
                      </div>
                    </div>
                  </div>
                </div>

                {!isAdmin && (
                  <div className="mt-4 bg-gray-700/30 border border-gray-600 rounded-lg p-3">
                    <div className="text-gray-300 text-xs">
                      👤 <strong>Regular User Access:</strong> You can browse and download all documentation from the library.
                      To generate new documentation, contact an administrator.
                    </div>
                  </div>
                )}
              </section>

              {/* Keyboard Shortcuts */}
              <section className="bg-black/40 rounded-xl border border-purple-500/30 p-5">
                <h3 className="text-xl font-bold text-purple-400 mb-3">⌨️ Keyboard Shortcuts</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                  <div className="flex items-center gap-2">
                    <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-xs font-mono">ESC</kbd>
                    <span className="text-gray-400 text-xs">Close help modal</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <kbd className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-xs font-mono">F1</kbd>
                    <span className="text-gray-400 text-xs">Open help (when implemented)</span>
                  </div>
                </div>
              </section>

              {/* Support */}
              <section className="bg-gradient-to-r from-blue-900/20 to-emerald-900/20 rounded-xl border border-gray-700 p-5">
                <h3 className="text-lg font-bold text-white mb-2">💬 Need More Help?</h3>
                <p className="text-gray-400 text-sm">
                  If you encounter any issues or have questions not covered in this guide, please contact your system administrator.
                </p>
              </section>
            </div>

            {/* Footer */}
            <div className="sticky bottom-0 bg-gray-900/90 backdrop-blur border-t border-gray-700 px-6 py-4">
              <div className="flex justify-between items-center text-xs text-gray-500">
                <span>GUI Agent v2.1</span>
                <button
                  onClick={() => setShowHelp(false)}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition font-semibold text-sm"
                >
                  Got it, thanks!
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
