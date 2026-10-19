import React, { useEffect, useState } from 'react';
import {
  Cpu,
  ShieldAlert,
  Power,
  CheckCircle2,
  AlertTriangle,
  Info,
  Clock,
  Layers,
  Code2,
  RefreshCw,
  X,
} from 'lucide-react';
import { api } from '../api/client';
import { ConnectorInfo } from '../types';

export const ConnectorsPage: React.FC = () => {
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedManifest, setSelectedManifest] = useState<ConnectorInfo | null>(null);
  const [togglingKey, setTogglingKey] = useState<string | null>(null);

  const fetchConnectors = async () => {
    setLoading(true);
    try {
      const data = await api.getConnectors();
      setConnectors(data.connectors);
    } catch (err: any) {
      console.error('Failed to load connectors:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConnectors();
  }, []);

  const handleToggleKillSwitch = async (key: string) => {
    setTogglingKey(key);
    try {
      const res = await api.toggleConnectorKillSwitch(key);
      setConnectors((prev) =>
        prev.map((c) => (c.key === key ? { ...c, disabled: res.disabled, health: res.disabled ? 'disabled' : 'healthy' } : c))
      );
    } catch (err: any) {
      alert(`Failed to toggle kill-switch for ${key}: ${err.message}`);
    } finally {
      setTogglingKey(null);
    }
  };

  return (
    <div id="page-connectors" className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800 pb-5">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <span>Connector Registry & Health Telemetry</span>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              {connectors.length} Modules Loaded
            </span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Contract-driven manifest registry, surface limits, error code maps, and instant emergency kill-switch toggles.
          </p>
        </div>

        <button
          onClick={fetchConnectors}
          id="refresh-connectors-btn"
          disabled={loading}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-medium border border-gray-700 transition self-start"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
          <span>Refresh Registry</span>
        </button>
      </div>

      {/* Connector Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {connectors.map((c) => (
          <div
            key={c.key}
            id={`connector-card-${c.key}`}
            className={`p-5 rounded-xl border transition flex flex-col justify-between ${
              c.disabled
                ? 'bg-red-950/20 border-red-500/40'
                : 'bg-gray-900/70 border-gray-800 hover:border-gray-700'
            }`}
          >
            <div>
              {/* Card Header */}
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-base font-bold text-white capitalize">{c.key}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-800 text-gray-300">
                      v{c.version}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold">
                      {c.tier}
                    </span>
                    <span className="text-[10px] font-mono uppercase text-gray-400">
                      Auth: {c.auth}
                    </span>
                  </div>
                </div>

                {/* Kill Switch Toggle */}
                <button
                  onClick={() => handleToggleKillSwitch(c.key)}
                  disabled={togglingKey === c.key}
                  id={`kill-switch-${c.key}`}
                  title={c.disabled ? 'Re-enable Connector' : 'Emergency Kill-Switch (Disable)'}
                  className={`flex items-center space-x-1 text-[11px] font-mono font-bold px-2.5 py-1 rounded-lg border transition ${
                    c.disabled
                      ? 'bg-red-500/20 text-red-300 border-red-500/40 hover:bg-emerald-900/40 hover:text-emerald-300 hover:border-emerald-500/40'
                      : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-red-900/40 hover:text-red-300 hover:border-red-500/40'
                  }`}
                >
                  <Power className={`w-3.5 h-3.5 ${togglingKey === c.key ? 'animate-spin' : ''}`} />
                  <span>{c.disabled ? 'KILL-SWITCHED' : 'ACTIVE'}</span>
                </button>
              </div>

              {/* Rate Limits & Surface Limits */}
              <div className="mt-4 space-y-2 text-xs">
                <div className="flex items-center justify-between p-2 rounded bg-gray-800/50 border border-gray-800 font-mono text-[11px]">
                  <span className="text-gray-400 flex items-center gap-1">
                    <Clock className="w-3 h-3 text-sky-400" /> Rate Limit:
                  </span>
                  <span className="text-gray-200 font-semibold">
                    {c.rate_limits?.per_connection?.requests || 30} req / {c.rate_limits?.per_connection?.per_seconds || 60}s
                  </span>
                </div>

                <div className="p-2 rounded bg-gray-800/50 border border-gray-800 space-y-1">
                  <div className="text-[10px] uppercase font-mono text-gray-400">Surfaces & Caps:</div>
                  <div className="space-y-1">
                    {(c.surfaces || []).map((s, idx) => (
                      <div key={idx} className="flex justify-between items-center text-[11px] font-mono">
                        <span className="text-sky-300 font-medium">/{s.key}</span>
                        <span className="text-gray-400 text-[10px]">
                          {s.spec?.title_max_chars ? `Title ${s.spec.title_max_chars}c` : ''}
                          {s.spec?.body_max_chars ? ` • Body ${s.spec.body_max_chars}c` : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Capabilities */}
              <div className="mt-3">
                <div className="text-[10px] uppercase font-mono text-gray-400 mb-1">Capabilities:</div>
                <div className="flex flex-wrap gap-1">
                  {(c.capabilities || []).map((cap, idx) => (
                    <span
                      key={idx}
                      className="px-1.5 py-0.5 rounded bg-gray-800 text-gray-300 font-mono text-[10px]"
                    >
                      {cap}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Bottom Actions */}
            <div className="mt-4 pt-3 border-t border-gray-800/80 flex items-center justify-between text-xs">
              <span className="text-[11px] text-gray-400">
                {Object.keys(c.error_map || {}).length} Platform Error Maps
              </span>
              <button
                onClick={() => setSelectedManifest(c)}
                id={`view-manifest-btn-${c.key}`}
                className="text-sky-400 hover:text-sky-300 font-medium text-xs flex items-center gap-1"
              >
                <Code2 className="w-3.5 h-3.5" />
                <span>Manifest JSON</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Manifest Viewer Modal */}
      {selectedManifest && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0e1424] border border-gray-800 rounded-xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl">
            <div className="p-4 border-b border-gray-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Code2 className="w-4 h-4 text-sky-400" />
                  <span>Manifest Specification: {selectedManifest.key}.manifest.yaml</span>
                </h3>
                <p className="text-xs text-gray-400 mt-0.5">Strict schema-validated connector contract</p>
              </div>
              <button
                onClick={() => setSelectedManifest(null)}
                className="p-1 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto space-y-4">
              <div>
                <div className="text-xs font-bold text-gray-300 uppercase font-mono mb-1">Standard Platform Error Mapping:</div>
                <div className="bg-black/50 p-3 rounded-lg border border-gray-800 font-mono text-xs space-y-1">
                  {Object.entries(selectedManifest.error_map || {}).map(([raw, code]) => (
                    <div key={raw} className="flex justify-between items-center text-[11px]">
                      <span className="text-amber-400">{raw}</span>
                      <span className="text-gray-500">→</span>
                      <span className="text-emerald-400 font-semibold">{code}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="text-xs font-bold text-gray-300 uppercase font-mono mb-1">Full Manifest Payload:</div>
                <pre className="bg-black/50 p-3 rounded-lg border border-gray-800 font-mono text-xs text-gray-300 overflow-x-auto max-h-72">
                  {JSON.stringify(selectedManifest, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
