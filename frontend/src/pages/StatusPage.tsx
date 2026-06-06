import { useState, useEffect } from 'react';
import { healthApi } from '../lib/api';
import type { HealthStatus } from '../types';
import { Activity, Server, Brain, HardDrive, RefreshCw } from 'lucide-react';

export default function StatusPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const data = await healthApi.check();
      setHealth(data);
      setLastChecked(new Date());
    } catch {
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Activity className="w-6 h-6 text-indigo-400" />
            System Status
          </h2>
          <p className="text-gray-500 mt-1">
            {lastChecked
              ? `Last checked: ${lastChecked.toLocaleTimeString()}`
              : 'Loading…'}
          </p>
        </div>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="btn-secondary flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {health ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Server Status */}
          <div className="card flex items-start gap-4">
            <div className="p-3 bg-green-900/30 rounded-xl">
              <Server className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <h3 className="font-medium text-gray-200">Server</h3>
              <p className="text-2xl font-bold text-green-400 capitalize">{health.status}</p>
              <p className="text-sm text-gray-500 mt-1">
                WebSocket + REST API running
              </p>
            </div>
          </div>

          {/* AI Status */}
          <div className="card flex items-start gap-4">
            <div className={`p-3 rounded-xl ${health.ai_available ? 'bg-indigo-900/30' : 'bg-yellow-900/30'}`}>
              <Brain className={`w-6 h-6 ${health.ai_available ? 'text-indigo-400' : 'text-yellow-400'}`} />
            </div>
            <div>
              <h3 className="font-medium text-gray-200">Claude AI</h3>
              <p className={`text-2xl font-bold ${health.ai_available ? 'text-indigo-400' : 'text-yellow-400'}`}>
                {health.ai_available ? 'Online' : 'Offline'}
              </p>
              <p className="text-sm text-gray-500 mt-1">
                {health.ai_available ? 'All AI features available' : 'Set ANTHROPIC_API_KEY to enable'}
              </p>
            </div>
          </div>

          {/* Files */}
          <div className="card flex items-start gap-4">
            <div className="p-3 bg-blue-900/30 rounded-xl">
              <HardDrive className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h3 className="font-medium text-gray-200">Files Available</h3>
              <p className="text-2xl font-bold text-blue-400">{health.files_count}</p>
              <p className="text-sm text-gray-500 mt-1">Served from files/ directory</p>
            </div>
          </div>

          {/* Tech Stack */}
          <div className="card">
            <h3 className="font-medium text-gray-200 mb-3">Tech Stack</h3>
            <div className="flex flex-wrap gap-2">
              {[
                'Python 3.12+', 'FastAPI', 'WebSockets', 'Claude AI',
                'React', 'TypeScript', 'Tailwind CSS', 'JWT Auth',
              ].map((tech) => (
                <span key={tech} className="px-2.5 py-1 bg-gray-800 rounded-lg text-xs text-gray-300 border border-gray-700">
                  {tech}
                </span>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="card text-center py-12">
          <p className="text-red-400 text-lg font-medium">Server Unreachable</p>
          <p className="text-gray-500 mt-2">
            Make sure the backend is running: <code className="text-gray-300">uvicorn api:app --reload</code>
          </p>
        </div>
      )}
    </div>
  );
}
