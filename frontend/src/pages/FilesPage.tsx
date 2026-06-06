import { useState, useEffect } from 'react';
import { filesApi } from '../lib/api';
import type { FileInfo, FileContent, FileSummary } from '../types';
import { FolderOpen, FileText, Search, Loader2, X, Sparkles } from 'lucide-react';

export default function FilesPage() {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<FileContent | null>(null);
  const [selectedName, setSelectedName] = useState('');
  const [loadingFile, setLoadingFile] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<string[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [summary, setSummary] = useState<string>('');
  const [summarizing, setSummarizing] = useState(false);

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    try {
      const data = await filesApi.list();
      setFiles(data);
    } catch (err) {
      console.error('Failed to load files:', err);
    } finally {
      setLoading(false);
    }
  };

  const openFile = async (filename: string) => {
    setLoadingFile(true);
    setSelectedName(filename);
    setSummary('');
    try {
      const data = await filesApi.get(filename);
      setSelectedFile(data);
    } catch {
      setSelectedFile(null);
    } finally {
      setLoadingFile(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await filesApi.search(searchQuery);
      setSearchResults(res.matches);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleSummarize = () => {
    if (!selectedName) return;
    setSummarizing(true);
    setSummary('');
    filesApi.summarize(
      selectedName,
      (token) => setSummary((prev) => prev + token),
      () => setSummarizing(false)
    );
  };

  const parseSummary = (raw: string): FileSummary | null => {
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  };

  return (
    <div className="flex h-full">
      {/* File list panel */}
      <div className="w-80 border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <FolderOpen className="w-5 h-5 text-indigo-400" />
            Files
          </h2>

          {/* Search */}
          <div className="mt-3 flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="input-field text-sm"
              placeholder="Search files…"
            />
            <button
              onClick={handleSearch}
              disabled={searching}
              className="btn-secondary p-2"
            >
              {searching ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
            </button>
          </div>

          {searchResults !== null && (
            <div className="mt-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">
                  {searchResults.length} match{searchResults.length !== 1 ? 'es' : ''}
                </span>
                <button
                  onClick={() => setSearchResults(null)}
                  className="text-xs text-gray-500 hover:text-gray-300"
                >
                  Clear
                </button>
              </div>
            </div>
          )}
        </div>

        {/* File list */}
        <div className="flex-1 overflow-y-auto p-2">
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-gray-500" />
            </div>
          ) : (
            <div className="space-y-1">
              {(searchResults ?? files.map((f) => f.name)).map((name) => {
                const file = files.find((f) => f.name === name);
                return (
                  <button
                    key={name}
                    onClick={() => openFile(name)}
                    className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
                      selectedName === name
                        ? 'bg-indigo-600/20 border border-indigo-500/30 text-indigo-300'
                        : 'hover:bg-gray-800 text-gray-300'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 shrink-0" />
                      <span className="text-sm font-medium truncate">{name}</span>
                    </div>
                    {file && (
                      <p className="text-xs text-gray-500 mt-0.5 ml-6">{file.size}</p>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* File content panel */}
      <div className="flex-1 flex flex-col">
        {selectedFile ? (
          <>
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white">{selectedName}</h3>
                <p className="text-sm text-gray-500">
                  {selectedFile.metadata.size_bytes.toLocaleString()} bytes •{' '}
                  {selectedFile.metadata.line_count} lines •{' '}
                  {selectedFile.metadata.mime_type}
                </p>
              </div>
              <div className="flex gap-2">
                <button onClick={handleSummarize} disabled={summarizing} className="btn-primary flex items-center gap-2 text-sm">
                  {summarizing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  Summarize
                </button>
                <button onClick={() => { setSelectedFile(null); setSelectedName(''); setSummary(''); }} className="p-2 text-gray-400 hover:text-gray-200 rounded-lg hover:bg-gray-800">
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Summary panel */}
            {summary && (
              <div className="px-6 py-4 border-b border-gray-800 bg-gray-900/50">
                <SummaryDisplay raw={summary} isStreaming={summarizing} />
              </div>
            )}

            {/* File content */}
            <div className="flex-1 overflow-y-auto p-6">
              <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap bg-gray-900 rounded-xl p-4 border border-gray-800">
                {selectedFile.content}
              </pre>
            </div>
          </>
        ) : loadingFile ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="p-4 bg-gray-900 rounded-full mb-4">
              <FileText className="w-8 h-8 text-indigo-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-300">Select a file</h3>
            <p className="text-gray-500 mt-1">Choose a file from the sidebar to view its content</p>
          </div>
        )}
      </div>
    </div>
  );
}

function SummaryDisplay({ raw, isStreaming }: { raw: string; isStreaming: boolean }) {
  const parsed = (() => {
    try {
      return JSON.parse(raw) as FileSummary;
    } catch {
      return null;
    }
  })();

  if (!parsed) {
    return (
      <div className={`text-sm text-gray-300 ${isStreaming ? 'streaming-cursor' : ''}`}>
        {raw}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div>
        <h4 className="text-sm font-medium text-indigo-300 mb-1">Summary</h4>
        <p className="text-sm text-gray-300">{parsed.executive_summary}</p>
      </div>
      {parsed.key_topics.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-indigo-300 mb-1">Key Topics</h4>
          <div className="flex flex-wrap gap-2">
            {parsed.key_topics.map((topic, i) => (
              <span key={i} className="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-300">
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-indigo-300">Sentiment:</span>
        <span className={`text-sm px-2 py-0.5 rounded ${
          parsed.sentiment === 'positive' ? 'bg-green-900/30 text-green-300' :
          parsed.sentiment === 'negative' ? 'bg-red-900/30 text-red-300' :
          'bg-gray-800 text-gray-300'
        }`}>
          {parsed.sentiment}
        </span>
      </div>
    </div>
  );
}
