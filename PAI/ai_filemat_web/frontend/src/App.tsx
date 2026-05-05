import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';
import './App.css';

// Functional components will be integrated later

// Define types
interface FileInfo {
  id: string;
  name: string;
  size: number;
  type: string;
  category: string;
  icon: string;
  upload_time: string;
  path: string;
  metadata?: any;
}

// Professional Main Application Component
const AIFileMat = () => {
  const [activeTab, setActiveTab] = useState('home');
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [theme, setTheme] = useState('light');
  const [aiStatus, setAiStatus] = useState('connected');
  const [outputDir, setOutputDir] = useState('/home/user/Downloads/AIFileMat_Output');
  const [zoomLevel, setZoomLevel] = useState(100);
  
  // Zoom controls
  const minZoom = 50;
  const maxZoom = 200;
  const zoomStep = 10;
  
  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(prev + zoomStep, maxZoom));
  };
  
  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(prev - zoomStep, minZoom));
  };
  
  const handleZoomReset = () => {
    setZoomLevel(100);
  };

  // Tab configuration matching the desktop app
  const tabs = [
    { id: 'home', icon: '🏠', name: 'Home', description: 'Dashboard & quick actions' },
    { id: 'aichat', icon: '🤖', name: 'AI Chat', description: 'Chat with your files' },
    { id: 'command', icon: '🧠', name: 'AI Command', description: 'Natural language commands' },
    { id: 'convert', icon: '🔄', name: 'Convert', description: 'Format conversion' },
    { id: 'split', icon: '✂️', name: 'Split', description: 'Split documents' },
    { id: 'merge', icon: '🔗', name: 'Merge', description: 'Merge files' },
    { id: 'media', icon: '🎬', name: 'Media', description: 'Video & audio processing' },
    { id: 'organise', icon: '📐', name: 'Organise', description: 'File organization' },
    { id: 'upscale', icon: '🖼', name: 'Upscale', description: 'Image enhancement' },
    { id: 'stamp', icon: '💧', name: 'Stamp', description: 'Watermark & stamp' },
    { id: 'protect', icon: '🔒', name: 'Protect', description: 'Encryption & security' },
    { id: 'compress', icon: '📦', name: 'Compress', description: 'File compression' },
    { id: 'metadata', icon: '🏷', name: 'Metadata', description: 'File metadata' },
    { id: 'queue', icon: '📋', name: 'Queue', description: 'Processing queue' },
    { id: 'log', icon: '📜', name: 'Log', description: 'Operation history' },
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'home':
        return <HomeTab files={files} setFiles={setFiles} />;
      case 'aichat':
        return <AIChatTab files={files} aiStatus={aiStatus} />;
      case 'command':
        return <AICommandTab files={files} />;
      case 'convert':
        return <ConvertTab files={files} />;
      case 'split':
        return <SplitTab files={files} />;
      case 'merge':
        return <MergeTab files={files} />;
      case 'media':
        return <MediaTab files={files} />;
      case 'organise':
        return <OrganiseTab files={files} />;
      case 'upscale':
        return <UpscaleTab files={files} />;
      case 'stamp':
        return <StampTab files={files} />;
      case 'protect':
        return <ProtectTab files={files} />;
      case 'compress':
        return <CompressTab files={files} />;
      case 'metadata':
        return <MetadataTab files={files} />;
      case 'queue':
        return <QueueTab />;
      case 'log':
        return <LogTab />;
      default:
        return <HomeTab files={files} setFiles={setFiles} />;
    }
  };

  return (
    <div className={`min-h-screen ${theme === 'dark' ? 'dark' : ''}`}>
      <div className="bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 min-h-screen transition-colors duration-300">
        {/* Header */}
        <header className="bg-white dark:bg-gray-800 shadow-lg border-b border-gray-200 dark:border-gray-700">
          <div className="px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                    <span className="text-white font-bold text-sm">AI</span>
                  </div>
                  <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                    AI FileMat
                  </h1>
                </div>
                <div className="flex items-center space-x-2 text-sm">
                  <div className={`w-2 h-2 rounded-full ${aiStatus === 'connected' ? 'bg-green-500' : 'bg-red-500'} animate-pulse`}></div>
                  <span className="text-gray-600 dark:text-gray-400">
                    {aiStatus === 'connected' ? 'AI Connected' : 'AI Disconnected'}
                  </span>
                </div>
              </div>
              
              <div className="flex items-center space-x-4">
                {/* Output Directory */}
                <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                  <span>📁</span>
                  <span className="truncate max-w-xs">{outputDir}</span>
                </div>
                
                {/* Theme Toggle */}
                <button
                  onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
                  className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                >
                  {theme === 'light' ? '🌙' : '☀️'}
                </button>
                
                {/* Zoom Controls */}
                <div className="flex items-center space-x-1 text-sm text-gray-600 dark:text-gray-400">
                  <button
                    onClick={handleZoomOut}
                    disabled={zoomLevel <= minZoom}
                    className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    title="Zoom Out"
                  >
                    ➖
                  </button>
                  <span className="px-2 font-medium">{zoomLevel}%</span>
                  <button
                    onClick={handleZoomIn}
                    disabled={zoomLevel >= maxZoom}
                    className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    title="Zoom In"
                  >
                    ➕
                  </button>
                  <button
                    onClick={handleZoomReset}
                    className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                    title="Reset Zoom"
                  >
                    🔄
                  </button>
                </div>
                
                {/* Settings */}
                <button className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
                  ⚙️
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="flex h-screen pt-16">
          {/* Sidebar */}
          <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 overflow-y-auto">
            <div className="p-4">
              <div className="space-y-1">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg transition-all duration-200 flex items-center space-x-3 ${
                      activeTab === tab.id
                        ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg transform scale-105'
                        : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                    }`}
                  >
                    <span className="text-lg">{tab.icon}</span>
                    <div className="flex-1">
                      <div className="font-medium">{tab.name}</div>
                      <div className={`text-xs ${activeTab === tab.id ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400'}`}>
                        {tab.description}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Content Area */}
          <div className="flex-1 overflow-hidden">
            <div 
              className="h-full overflow-y-auto transition-transform duration-200 ease-in-out"
              style={{ 
                transform: `scale(${zoomLevel / 100})`,
                transformOrigin: 'top left'
              }}
            >
              {renderTabContent()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Tab Components with real functionality
const HomeTab = ({ files, setFiles }: { files: FileInfo[], setFiles: (files: FileInfo[]) => void }) => {
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);

  const handleFilesUploaded = (uploadedFiles: any[]) => {
    setFiles([...files, ...uploadedFiles]);
  };

  const handleFilesChange = (updatedFiles: FileInfo[]) => {
    setFiles(updatedFiles);
  };

  return (
    <div className="p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Welcome to AI FileMat
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Advanced file processing with AI intelligence
          </p>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Files</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{files.length}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
                <span className="text-2xl">📁</span>
              </div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Selected</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{selectedFiles.length}</p>
              </div>
              <div className="w-12 h-12 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center">
                <span className="text-2xl">✓</span>
              </div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">File Types</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {new Set(files.map(f => f.category)).size}
                </p>
              </div>
              <div className="w-12 h-12 bg-yellow-100 dark:bg-yellow-900 rounded-lg flex items-center justify-center">
                <span className="text-2xl">📊</span>
              </div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Size</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {(files.reduce((total, f) => total + f.size, 0) / 1024 / 1024).toFixed(1)} MB
                </p>
              </div>
              <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center">
                <span className="text-2xl">💾</span>
              </div>
            </div>
          </div>
        </div>

        {/* File Upload - Placeholder for now */}
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Upload Files</h3>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-8 shadow-lg border-2 border-dashed border-gray-300 dark:border-gray-700">
            <div className="text-center">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">📁</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Drop files here or click to browse
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Support for PDF, DOCX, XLSX, PPTX, Images, Audio, Video and more
              </p>
              <button className="px-6 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-lg hover:from-blue-600 hover:to-indigo-700 transition-all duration-200 shadow-lg">
                Select Files
              </button>
            </div>
          </div>
        </div>

        {/* File List - Placeholder */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Uploaded Files</h3>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="p-6">
              <div className="text-center text-gray-500 dark:text-gray-400">
                {files.length === 0 ? 'No files uploaded yet. Drop files above to get started.' : `${files.length} file(s) uploaded`}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const AIChatTab = ({ files, aiStatus }: { files: FileInfo[], aiStatus: string }) => (
  <div className="p-6">
    <div className="max-w-4xl mx-auto h-full">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">AI Chat Assistant</h2>
          <p className="text-gray-600 dark:text-gray-400">Chat with your files using AI intelligence</p>
        </div>
        <div className="p-6">
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-4">
            <div className="flex items-center space-x-2 mb-2">
              <div className="w-8 h-8 bg-gradient-to-br from-green-500 to-emerald-600 rounded-full flex items-center justify-center">
                <span className="text-white text-sm">AI</span>
              </div>
              <span className="font-medium text-gray-900 dark:text-white">AI Assistant</span>
            </div>
            <p className="text-gray-700 dark:text-gray-300">
              Hello! I'm your AI FileMat assistant. I can help you process, analyze, and convert your files using natural language. What would you like to do today?
            </p>
          </div>
          
          <div className="flex space-x-2">
            <input
              type="text"
              placeholder="Ask me anything about your files..."
              className="flex-1 px-4 py-3 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 dark:text-white"
            />
            <button className="px-6 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-lg hover:from-blue-600 hover:to-indigo-700 transition-all duration-200">
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
);

// Placeholder components for other tabs with proper types
const AICommandTab = ({ files }: { files: FileInfo[] }) => (
  <div className="p-6">
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">AI Command Center</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="text-gray-600 dark:text-gray-400">Natural language file operations coming soon...</p>
      </div>
    </div>
  </div>
);

const ConvertTab = ({ files }: { files: FileInfo[] }) => (
  <div className="p-6">
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">File Converter</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="text-gray-600 dark:text-gray-400">Advanced file conversion tools coming soon...</p>
      </div>
    </div>
  </div>
);

const SplitTab = ({ files }: { files: FileInfo[] }) => (
  <div className="p-6">
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">File Splitter</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="text-gray-600 dark:text-gray-400">Document splitting tools coming soon...</p>
      </div>
    </div>
  </div>
);

const MergeTab = ({ files }: { files: FileInfo[] }) => (
  <div className="p-6">
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">File Merger</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="text-gray-600 dark:text-gray-400">File merging tools coming soon...</p>
      </div>
    </div>
  </div>
);

const MediaTab = ({ files }: { files: FileInfo[] }) => (
  <div className="p-6">
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Media Processing</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="text-gray-600 dark:text-gray-400">Video and audio processing tools coming soon...</p>
      </div>
    </div>
  </div>
);

const OrganiseTab = ({ files }: { files: FileInfo[] }) => (
  <div className="p-6">
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">File Organizer</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="text-gray-600 dark:text-gray-400">File organization tools coming soon...</p>
      </div>
    </div>
  </div>
);

const UpscaleTab = ({ files }: { files: FileInfo[] }) => (
  <div className="p-6">
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Image Upscaler</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="text-gray-600 dark:text-gray-400">AI image enhancement tools coming soon...</p>
      </div>
    </div>
  </div>
);

const StampTab = ({ files }: { files: FileInfo[] }) => (
  <div className="p-6">
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Watermark & Stamp</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="text-gray-600 dark:text-gray-400">Watermarking tools coming soon...</p>
      </div>
    </div>
  </div>
);

const ProtectTab = ({ files }: { files: FileInfo[] }) => (
  <div className="p-6">
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">File Protection</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="text-gray-600 dark:text-gray-400">Encryption and security tools coming soon...</p>
      </div>
    </div>
  </div>
);

const CompressTab = ({ files }: { files: FileInfo[] }) => (
  <div className="p-6">
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">File Compression</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="text-gray-600 dark:text-gray-400">Compression tools coming soon...</p>
      </div>
    </div>
  </div>
);

const MetadataTab = ({ files }: { files: FileInfo[] }) => (
  <div className="p-6">
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">File Metadata</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="text-gray-600 dark:text-gray-400">Metadata editing tools coming soon...</p>
      </div>
    </div>
  </div>
);

const QueueTab = () => (
  <div className="p-6">
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Processing Queue</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="text-gray-600 dark:text-gray-400">Queue management coming soon...</p>
      </div>
    </div>
  </div>
);

const LogTab = () => (
  <div className="p-6">
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Operation Log</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="text-gray-600 dark:text-gray-400">Operation history coming soon...</p>
      </div>
    </div>
  </div>
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/" element={<AIFileMat />} />
          <Route path="/*" element={<AIFileMat />} />
        </Routes>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: 'white',
              color: 'black',
              border: '1px solid #ccc',
              borderRadius: '0.75rem',
              fontSize: '0.875rem',
            },
          }}
        />
      </Router>
    </QueryClientProvider>
  );
}

export default App;
