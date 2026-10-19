import React, { useEffect, useState } from 'react';
import {
  Award,
  Play,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  ExternalLink,
  ShieldAlert,
  Layers,
  FileCheck2,
  RefreshCw,
  Info,
} from 'lucide-react';
import { api } from '../api/client';
import { CertificationAlert, CertificationRecord, Destination, StepResult } from '../types';

interface CertificationPageProps {
  initialDestinationId?: string;
}

const ALL_STEPS = [
  'prerequisites',
  'validate',
  'publish',
  'confirm_live',
  'get_status',
  'delete',
  'store_evidence',
  'set_level',
];

export const CertificationPage: React.FC<CertificationPageProps> = ({ initialDestinationId }) => {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [selectedDestId, setSelectedDestId] = useState<string>(initialDestinationId || '');
  const [isMock, setIsMock] = useState<boolean>(true);
  const [running, setRunning] = useState<boolean>(false);
  const [activeCertRecord, setActiveCertRecord] = useState<CertificationRecord | null>(null);
  const [history, setHistory] = useState<CertificationRecord[]>([]);
  const [alerts, setAlerts] = useState<CertificationAlert[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchPageData = async () => {
    setLoading(true);
    try {
      const [dests, alertList] = await Promise.all([
        api.getDestinations().catch(() => []),
        api.getCertificationAlerts().catch(() => []),
      ]);
      setDestinations(dests);
      setAlerts(alertList);

      const targetId = selectedDestId || (dests.length > 0 ? dests[0].id : '');
      if (targetId) {
        if (!selectedDestId) setSelectedDestId(targetId);
        const hist = await api.getCertificationHistory(targetId).catch(() => []);
        setHistory(hist);
        if (hist.length > 0 && !activeCertRecord) {
          setActiveCertRecord(hist[0]);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPageData();
  }, []);

  const handleSelectDestination = async (id: string) => {
    setSelectedDestId(id);
    try {
      const hist = await api.getCertificationHistory(id);
      setHistory(hist);
      setActiveCertRecord(hist.length > 0 ? hist[0] : null);
    } catch {
      setHistory([]);
      setActiveCertRecord(null);
    }
  };

  const handleRunCertification = async () => {
    if (!selectedDestId) return;
    setRunning(true);
    try {
      const result = await api.runCertification(selectedDestId, isMock);
      setActiveCertRecord(result);
      const hist = await api.getCertificationHistory(selectedDestId);
      setHistory(hist);
      // Refresh destinations to reflect new level
      const dests = await api.getDestinations();
      setDestinations(dests);
    } catch (err: any) {
      alert(`Certification failed: ${err.message}`);
    } finally {
      setRunning(false);
    }
  };

  const selectedDest = destinations.find((d) => d.id === selectedDestId);

  // Normalize step results so all 8 steps show
  const stepResultsMap = new Map<string, StepResult>();
  if (activeCertRecord?.step_results) {
    activeCertRecord.step_results.forEach((s) => stepResultsMap.set(s.step_name, s));
  }

  return (
    <div id="page-certification" className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800 pb-5">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <span>Certification Center & Contract Verification</span>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              8-Step Harness
            </span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Automated lifecycle validation: prerequisites, test post, confirm live, cleanup deletion within 10m, and evidence retention.
          </p>
        </div>

        <button
          onClick={fetchPageData}
          id="refresh-certification-btn"
          disabled={loading || running}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-medium border border-gray-700 transition self-start"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Control & Trigger Panel */}
      <div className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end">
          <div className="md:col-span-6">
            <label className="block text-xs font-medium text-gray-300 mb-1">Target Destination</label>
            <select
              id="cert-destination-select"
              value={selectedDestId}
              onChange={(e) => handleSelectDestination(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
            >
              {destinations.map((d) => (
                <option key={d.id} value={d.id}>
                  [{d.level || 'L0'}] {d.name} ({d.platform_key})
                </option>
              ))}
            </select>
          </div>

          <div className="md:col-span-3">
            <label className="block text-xs font-medium text-gray-300 mb-1">Execution Mode</label>
            <div className="flex items-center space-x-2 bg-gray-800 p-1.5 rounded-lg border border-gray-700 text-xs">
              <button
                type="button"
                id="cert-mode-mock-btn"
                onClick={() => setIsMock(true)}
                className={`flex-1 py-1 rounded font-mono font-bold text-center transition ${
                  isMock
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                MOCK SANDBOX
              </button>
              <button
                type="button"
                id="cert-mode-real-btn"
                onClick={() => setIsMock(false)}
                className={`flex-1 py-1 rounded font-mono font-bold text-center transition ${
                  !isMock
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                REAL PLATFORM
              </button>
            </div>
          </div>

          <div className="md:col-span-3">
            <button
              onClick={handleRunCertification}
              disabled={running || !selectedDestId}
              id="trigger-certification-btn"
              className="w-full py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center justify-center space-x-2 transition shadow-md disabled:bg-gray-800 disabled:text-gray-500"
            >
              <Play className={`w-3.5 h-3.5 ${running ? 'animate-spin' : ''}`} />
              <span>{running ? 'Executing 8-Step Lifecycle...' : 'Run Certification'}</span>
            </button>
          </div>
        </div>

        {/* Mock vs Real Disclaimer Banner */}
        <div className="p-3 rounded-lg bg-black/40 border border-amber-500/30 flex items-start space-x-3 text-xs text-amber-200">
          <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold text-amber-300">Certification Guarantee: </span>
            Runs executed with <span className="font-mono bg-black/60 px-1 py-0.5 rounded text-amber-400">is_mock: true</span> are permanently labeled <span className="font-mono font-bold text-amber-300">mock</span> in the audit manifest and can never grant a real-certified tier. Real-certified level requires live verification against the target container or API.
          </div>
        </div>
      </div>

      {/* 8-Step Timeline View */}
      <div className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Award className="w-4 h-4 text-emerald-400" />
              <span>8-Step Lifecycle Execution Timeline</span>
            </h2>
            {selectedDest && (
              <p className="text-xs text-gray-400 mt-0.5 font-mono">
                Destination: {selectedDest.name} • Level: {selectedDest.level || 'L0'}
              </p>
            )}
          </div>

          {activeCertRecord && (
            <div className="flex items-center space-x-3">
              <span
                id="cert-mock-real-badge"
                className={`px-2.5 py-0.5 rounded-full font-mono text-[11px] font-bold border ${
                  activeCertRecord.is_mock
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                }`}
              >
                {activeCertRecord.is_mock ? 'MOCK RUN' : 'REAL PLATFORM CERTIFIED'}
              </span>

              <span
                id="cert-overall-status-badge"
                className={`px-2.5 py-0.5 rounded font-mono text-[11px] font-bold ${
                  activeCertRecord.status === 'succeeded'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : activeCertRecord.status === 'failed'
                    ? 'bg-red-500/20 text-red-400'
                    : 'bg-sky-500/20 text-sky-400'
                }`}
              >
                {activeCertRecord.status.toUpperCase()} ({activeCertRecord.assigned_level})
              </span>
            </div>
          )}
        </div>

        {/* Step Timeline Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
          {ALL_STEPS.map((stepName, idx) => {
            const stepResult = stepResultsMap.get(stepName);
            const status = stepResult ? stepResult.status : 'pending';

            return (
              <div
                key={stepName}
                id={`timeline-step-${stepName}`}
                className={`p-3.5 rounded-xl border flex flex-col justify-between transition ${
                  status === 'succeeded'
                    ? 'bg-emerald-950/20 border-emerald-500/30'
                    : status === 'failed'
                    ? 'bg-red-950/30 border-red-500/40'
                    : status === 'running'
                    ? 'bg-sky-950/30 border-sky-500/40 animate-pulse'
                    : 'bg-gray-800/30 border-gray-800'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="font-mono text-gray-500 text-[10px]">STEP {idx + 1}/8</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                        status === 'succeeded'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : status === 'failed'
                          ? 'bg-red-500/20 text-red-400'
                          : status === 'running'
                          ? 'bg-sky-500/20 text-sky-400'
                          : 'bg-gray-800 text-gray-400'
                      }`}
                    >
                      {status}
                    </span>
                  </div>

                  <div className="font-bold text-white text-xs font-mono capitalize">
                    {stepName.replace('_', ' ')}
                  </div>

                  {stepResult?.error_message && (
                    <div className="mt-1.5 text-[10px] text-red-300 bg-red-950/50 p-1.5 rounded border border-red-500/30 font-mono">
                      {stepResult.error_message}
                    </div>
                  )}
                </div>

                <div className="mt-3 pt-2 border-t border-gray-800/60 flex items-center justify-between text-[10px] text-gray-400 font-mono">
                  <span>{stepResult?.duration_ms ? `${stepResult.duration_ms}ms` : '—'}</span>
                  {status === 'succeeded' && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                  {status === 'failed' && <XCircle className="w-3 h-3 text-red-400" />}
                </div>
              </div>
            );
          })}
        </div>

        {/* Evidence Artifact Links */}
        {activeCertRecord?.evidence_s3_url && (
          <div className="p-3.5 rounded-lg bg-gray-900 border border-gray-800 flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              <FileCheck2 className="w-4 h-4 text-sky-400" />
              <span className="text-gray-300 font-medium">Evidence Pack Stored:</span>
              <span className="font-mono text-sky-400 truncate max-w-sm">
                {activeCertRecord.evidence_s3_url}
              </span>
            </div>
            <a
              href={activeCertRecord.evidence_s3_url}
              target="_blank"
              rel="noreferrer"
              id="download-evidence-link"
              className="text-sky-400 hover:underline flex items-center gap-1 font-mono text-[11px]"
            >
              <span>Download Evidence JSON</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        )}
      </div>

      {/* Contract Breakage and Demotion Alerts */}
      <div className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-red-400" />
            <span>Contract Breakage & Demotion Alerts ({alerts.length})</span>
          </h2>
          <span className="text-xs text-gray-400 font-mono">Automatic exclusion from publishing</span>
        </div>

        {alerts.length === 0 ? (
          <div className="text-center py-6 text-gray-500 text-xs">
            No active contract breakage or demotion alerts. All destinations conform to certified specifications.
          </div>
        ) : (
          <div className="space-y-2">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="p-3.5 rounded-lg bg-red-950/20 border border-red-500/30 flex items-start justify-between text-xs"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-red-400 font-bold uppercase">{alert.alert_type}</span>
                    <span className="text-gray-400 font-mono">
                      Demoted from {alert.previous_level} → {alert.demoted_to}
                    </span>
                  </div>
                  <div className="text-gray-200">{alert.reason}</div>
                  {alert.evidence_s3_url && (
                    <div className="text-[10px] text-gray-400 font-mono">Evidence: {alert.evidence_s3_url}</div>
                  )}
                </div>
                <div className="text-[10px] text-gray-400 font-mono">
                  {new Date(alert.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
