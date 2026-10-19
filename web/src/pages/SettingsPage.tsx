import React, { useEffect, useState } from 'react';
import {
  Settings,
  ShieldCheck,
  ShieldAlert,
  KeyRound,
  Zap,
  BookOpen,
  ExternalLink,
  RefreshCw,
  Lock,
  Radio,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../api/client';
import { SecurityStatus } from '../types';

export const SettingsPage: React.FC = () => {
  const [tokenInput, setTokenInput] = useState<string>(api.getToken());
  const [status, setStatus] = useState<SecurityStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchSecurityStatus = async () => {
    setLoading(true);
    try {
      const data = await api.getSecurityStatus();
      setStatus(data);
    } catch (err: any) {
      console.error('Failed to load security status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSecurityStatus();
  }, []);

  const handleSaveToken = () => {
    api.setToken(tokenInput.trim());
    setActionMessage('Active demo token updated in client storage.');
    fetchSecurityStatus();
  };

  const handleRevokeToken = async () => {
    try {
      const res = await api.revokeToken(tokenInput.trim());
      setActionMessage(res.message);
      await fetchSecurityStatus();
    } catch (err: any) {
      alert(`Revoke failed: ${err.message}`);
    }
  };

  const handleRestoreToken = async () => {
    try {
      const res = await api.restoreToken(tokenInput.trim());
      setActionMessage(res.message);
      await fetchSecurityStatus();
    } catch (err: any) {
      alert(`Restore failed: ${err.message}`);
    }
  };

  const handleToggleSimulationMode = async () => {
    if (!status) return;
    try {
      const next = !status.simulation_mode;
      const res = await api.setSimulationMode(next);
      setActionMessage(res.message);
      await fetchSecurityStatus();
    } catch (err: any) {
      alert(`Toggle failed: ${err.message}`);
    }
  };

  return (
    <div id="page-settings" className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800 pb-5">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <span>Platform Security & Engine Configuration</span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Configure revocable reviewer authentication tokens, inspect rate limits, toggle simulation mode, and access interactive API documentation.
          </p>
        </div>

        <button
          onClick={fetchSecurityStatus}
          id="refresh-settings-btn"
          disabled={loading}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-medium border border-gray-700 transition self-start"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {actionMessage && (
        <div className="p-3.5 rounded-xl bg-sky-950/40 border border-sky-500/40 text-xs text-sky-300 flex items-center justify-between">
          <span>{actionMessage}</span>
          <button onClick={() => setActionMessage(null)} className="text-gray-400 hover:text-white">✕</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revocable Token Protection */}
        <div className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <KeyRound className="w-4 h-4 text-emerald-400" />
              <span>Revocable Demo API Token (X-IncuBrix-Token)</span>
            </h2>
            <span
              id="settings-token-status-badge"
              className={`px-2.5 py-0.5 rounded font-mono text-[11px] font-bold ${
                status?.status === 'active'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse'
              }`}
            >
              {status?.status?.toUpperCase() || 'ACTIVE'}
            </span>
          </div>

          <p className="text-xs text-gray-400 leading-relaxed">
            All API requests from this dashboard pass this revocable token header. If revoked, requests will be blocked with a 401 Unauthorized code.
          </p>

          <div className="space-y-2">
            <label className="block text-xs font-medium text-gray-300">Active Reviewer Token</label>
            <input
              type="text"
              id="demo-token-input"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-xs text-white font-mono focus:outline-none focus:border-sky-500"
            />
          </div>

          <div className="flex flex-wrap gap-2 pt-2">
            <button
              onClick={handleSaveToken}
              id="save-token-btn"
              className="px-3 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs transition"
            >
              Save Token
            </button>

            {status?.status === 'active' ? (
              <button
                onClick={handleRevokeToken}
                id="revoke-token-btn"
                className="px-3 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white font-bold text-xs transition"
              >
                Revoke Token Immediately
              </button>
            ) : (
              <button
                onClick={handleRestoreToken}
                id="restore-token-btn"
                className="px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs transition"
              >
                Restore Revoked Token
              </button>
            )}
          </div>
        </div>

        {/* Simulation Mode & Rate Limits */}
        <div className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              <span>Simulation Mode & Rate Limiting</span>
            </h2>
            <span
              id="settings-simulation-mode-badge"
              className={`px-2.5 py-0.5 rounded font-mono text-[11px] font-bold ${
                status?.simulation_mode
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  : 'bg-gray-800 text-gray-400'
              }`}
            >
              {status?.simulation_mode ? 'ENABLED' : 'DISABLED'}
            </span>
          </div>

          <p className="text-xs text-gray-400 leading-relaxed">
            Ensures all outbound dispatches target containerized mock platforms and isolated sandboxes without external production side-effects.
          </p>

          <div className="p-3.5 rounded-lg bg-gray-800/60 border border-gray-800 flex items-center justify-between text-xs">
            <div>
              <div className="font-semibold text-white">Global Simulation Mode Flag</div>
              <div className="text-[11px] text-gray-400">Controls top warning banner and certification mock labels</div>
            </div>
            <button
              onClick={handleToggleSimulationMode}
              id="settings-toggle-sim-mode-btn"
              className={`px-3 py-1.5 rounded-lg font-bold text-xs font-mono transition ${
                status?.simulation_mode
                  ? 'bg-amber-500 text-black hover:bg-amber-400'
                  : 'bg-gray-700 text-gray-200 hover:bg-gray-600'
              }`}
            >
              {status?.simulation_mode ? 'Sim: ACTIVE' : 'Sim: OFF'}
            </button>
          </div>

          <div className="p-3.5 rounded-lg bg-black/40 border border-gray-800 space-y-2 text-xs font-mono">
            <div className="text-gray-400 text-[11px] uppercase font-bold">Rate Limits Telemetry (Demo Tier):</div>
            <div className="flex justify-between">
              <span className="text-gray-400">Hourly Capacity:</span>
              <span className="text-white font-bold">{status?.rate_limits?.limit_per_minute || 120} req / min</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Remaining Quota:</span>
              <span className="text-emerald-400 font-bold">{status?.rate_limits?.remaining || 118} requests</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Window Reset:</span>
              <span className="text-sky-400 font-bold">{status?.rate_limits?.reset_seconds || 60} seconds</span>
            </div>
          </div>
        </div>

        {/* Webhook Secret & Cryptographic Verification */}
        <div className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-3">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Lock className="w-4 h-4 text-purple-400" />
            <span>Webhook HMAC-SHA256 Signing Secret</span>
          </h2>
          <p className="text-xs text-gray-400 leading-relaxed">
            All asynchronous callback payloads sent to <span className="font-mono text-gray-300">callback_url</span> are signed with this secret in header <span className="font-mono text-purple-400">X-IncuBrix-Signature</span>.
          </p>
          <div className="p-3 rounded-lg bg-black/40 border border-gray-800 font-mono text-xs text-purple-300 flex justify-between items-center">
            <span>Signing Secret:</span>
            <span className="font-bold">{status?.webhook_signing_secret || 'whsec_dev_***'}</span>
          </div>
        </div>

        {/* Documentation Portal Link */}
        <div className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-3 flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-sky-400" />
              <span>Interactive Swagger & OpenAPI Documentation</span>
            </h2>
            <p className="text-xs text-gray-400 mt-1 leading-relaxed">
              Explore and execute requests against all live endpoints (/docs, /redoc, /openapi.json) with full schema models.
            </p>
          </div>

          <div className="pt-2">
            <a
              href="/docs"
              target="_blank"
              rel="noopener noreferrer"
              id="swagger-docs-link-card"
              className="w-full py-2.5 px-4 rounded-lg bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white font-bold text-xs flex items-center justify-center space-x-2 transition shadow"
            >
              <BookOpen className="w-4 h-4" />
              <span>Open Interactive API Documentation (/docs)</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
