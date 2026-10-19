import React, { useEffect, useState } from 'react';
import {
  MapPin,
  Cpu,
  FileCode2,
  ShieldCheck,
  CheckCircle2,
  AlertOctagon,
  ArrowRight,
  RefreshCw,
  HardDrive,
  Database,
  Radio,
  Clock,
  Layers,
} from 'lucide-react';
import { api } from '../api/client';
import { ConnectorInfo, Destination, JobRecord, RuleAudit, SystemReadiness } from '../types';
import { PageId } from '../components/Sidebar';

interface OverviewPageProps {
  onNavigate: (page: PageId) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ onNavigate }) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [audits, setAudits] = useState<RuleAudit[]>([]);
  const [readiness, setReadiness] = useState<SystemReadiness | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [dests, connRes, jobList, auditList, readyStatus] = await Promise.all([
        api.getDestinations().catch(() => []),
        api.getConnectors().catch(() => ({ connectors: [], count: 0 })),
        api.getJobs(15).catch(() => []),
        api.getRuleAudits().catch(() => []),
        api.getReadiness().catch(() => null),
      ]);

      setDestinations(dests);
      setConnectors(connRes.connectors);
      setJobs(jobList);
      setAudits(auditList);
      setReadiness(readyStatus);
      setLastRefreshed(new Date());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const totalAudience = destinations.reduce((sum, d) => sum + (d.est_audience || 0), 0);
  const l1PlusCount = destinations.filter((d) => d.level && d.level !== 'L0').length;
  const l0Count = destinations.filter((d) => !d.level || d.level === 'L0').length;
  const activeConnectors = connectors.filter((c) => !c.disabled).length;
  const disabledConnectors = connectors.filter((c) => c.disabled).length;

  const succeededJobs = jobs.filter((j) => j.status === 'succeeded').length;
  const runningJobs = jobs.filter((j) => j.status === 'running' || j.status === 'queued').length;
  const failedJobs = jobs.filter((j) => j.status === 'failed').length;

  return (
    <div id="page-overview" className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800 pb-5">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <span>System Telemetry & Live Overview</span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Real-time control plane across {destinations.length} catalogue destinations, {connectors.length} registered connectors, and durable background jobs.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <span className="text-xs text-gray-400 font-mono">
            Synced: {lastRefreshed.toLocaleTimeString()}
          </span>
          <button
            onClick={fetchDashboardData}
            id="refresh-overview-btn"
            disabled={loading}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-medium border border-gray-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Destinations Metric */}
        <div
          onClick={() => onNavigate('destinations')}
          className="p-5 rounded-xl bg-gray-900/80 border border-gray-800 hover:border-sky-500/50 cursor-pointer transition shadow-sm group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Catalogue Destinations</span>
            <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400 group-hover:scale-110 transition">
              <MapPin className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-black text-white font-mono">{destinations.length}</span>
            <span className="text-xs text-emerald-400 font-medium">({l1PlusCount} certified)</span>
          </div>
          <div className="mt-2 text-xs text-gray-400 flex items-center justify-between">
            <span>{totalAudience.toLocaleString()} est. reach</span>
            <span className="text-sky-400 group-hover:translate-x-1 transition flex items-center">
              Explore <ArrowRight className="w-3 h-3 ml-0.5" />
            </span>
          </div>
        </div>

        {/* Connectors Metric */}
        <div
          onClick={() => onNavigate('connectors')}
          className="p-5 rounded-xl bg-gray-900/80 border border-gray-800 hover:border-indigo-500/50 cursor-pointer transition shadow-sm group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Active Connectors</span>
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 group-hover:scale-110 transition">
              <Cpu className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-black text-white font-mono">{activeConnectors}</span>
            <span className="text-xs text-gray-400 font-mono">/ {connectors.length} loaded</span>
          </div>
          <div className="mt-2 text-xs text-gray-400 flex items-center justify-between">
            <span>{disabledConnectors > 0 ? `${disabledConnectors} kill-switched` : 'All healthy'}</span>
            <span className="text-indigo-400 group-hover:translate-x-1 transition flex items-center">
              Manage <ArrowRight className="w-3 h-3 ml-0.5" />
            </span>
          </div>
        </div>

        {/* Durable Jobs Metric */}
        <div
          onClick={() => onNavigate('jobs')}
          className="p-5 rounded-xl bg-gray-900/80 border border-gray-800 hover:border-emerald-500/50 cursor-pointer transition shadow-sm group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Durable Jobs</span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 group-hover:scale-110 transition">
              <FileCode2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-black text-white font-mono">{jobs.length}</span>
            <span className="text-xs text-emerald-400 font-medium font-mono">{succeededJobs} done</span>
          </div>
          <div className="mt-2 text-xs text-gray-400 flex items-center justify-between">
            <span>{runningJobs} running, {failedJobs} failed</span>
            <span className="text-emerald-400 group-hover:translate-x-1 transition flex items-center">
              Logs <ArrowRight className="w-3 h-3 ml-0.5" />
            </span>
          </div>
        </div>

        {/* Rule Audits Metric */}
        <div
          onClick={() => onNavigate('rules')}
          className="p-5 rounded-xl bg-gray-900/80 border border-gray-800 hover:border-amber-500/50 cursor-pointer transition shadow-sm group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Rule Evaluations</span>
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 group-hover:scale-110 transition">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-3xl font-black text-white font-mono">{audits.length}</span>
            <span className="text-xs text-amber-400 font-mono">pre-flight</span>
          </div>
          <div className="mt-2 text-xs text-gray-400 flex items-center justify-between">
            <span>Zero bypass guarantee</span>
            <span className="text-amber-400 group-hover:translate-x-1 transition flex items-center">
              Audits <ArrowRight className="w-3 h-3 ml-0.5" />
            </span>
          </div>
        </div>
      </div>

      {/* Infrastructure Readiness & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Health & Infrastructure Probe */}
        <div className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Radio className="w-4 h-4 text-sky-400" />
              <span>Readiness Probes (/ready)</span>
            </h3>
            <span
              className={`text-[11px] font-mono px-2 py-0.5 rounded font-semibold ${
                readiness?.status === 'ready'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
              }`}
            >
              {readiness?.status?.toUpperCase() || 'CHECKING'}
            </span>
          </div>

          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between text-xs p-2.5 rounded-lg bg-gray-800/50 border border-gray-800">
              <div className="flex items-center space-x-2.5">
                <Database className="w-4 h-4 text-indigo-400" />
                <span className="text-gray-300 font-medium">PostgreSQL Relational DB</span>
              </div>
              <span
                className={`font-mono font-semibold px-2 py-0.5 rounded text-[10px] ${
                  readiness?.checks.database === 'up'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-amber-500/20 text-amber-400'
                }`}
              >
                {readiness?.checks.database?.toUpperCase() || 'STANDBY'}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs p-2.5 rounded-lg bg-gray-800/50 border border-gray-800">
              <div className="flex items-center space-x-2.5">
                <RefreshCw className="w-4 h-4 text-sky-400" />
                <span className="text-gray-300 font-medium">Redis Queue / Memory Lock</span>
              </div>
              <span
                className={`font-mono font-semibold px-2 py-0.5 rounded text-[10px] ${
                  readiness?.checks.queue === 'up'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-amber-500/20 text-amber-400'
                }`}
              >
                {readiness?.checks.queue?.toUpperCase() || 'STANDBY'}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs p-2.5 rounded-lg bg-gray-800/50 border border-gray-800">
              <div className="flex items-center space-x-2.5">
                <HardDrive className="w-4 h-4 text-purple-400" />
                <span className="text-gray-300 font-medium">MinIO / S3 Artifact Storage</span>
              </div>
              <span
                className={`font-mono font-semibold px-2 py-0.5 rounded text-[10px] ${
                  readiness?.checks.storage === 'up'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-amber-500/20 text-amber-400'
                }`}
              >
                {readiness?.checks.storage?.toUpperCase() || 'STANDBY'}
              </span>
            </div>
          </div>
        </div>

        {/* Quick Dispatch & Certification Actions */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            <span>Operational Quick Actions</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            <button
              onClick={() => onNavigate('publish')}
              id="quick-action-publish"
              className="p-3.5 rounded-lg bg-gradient-to-br from-sky-900/40 to-indigo-900/40 border border-sky-500/30 hover:border-sky-400 text-left transition group"
            >
              <div className="font-semibold text-white text-xs flex items-center justify-between">
                <span>Compose & Publish Content</span>
                <ArrowRight className="w-3.5 h-3.5 text-sky-400 group-hover:translate-x-1 transition" />
              </div>
              <p className="text-[11px] text-gray-400 mt-1">
                Multi-surface tailoring, live pre-flight rules evaluation, and durable dispatch.
              </p>
            </button>

            <button
              onClick={() => onNavigate('certification')}
              id="quick-action-certification"
              className="p-3.5 rounded-lg bg-gradient-to-br from-emerald-900/40 to-teal-900/40 border border-emerald-500/30 hover:border-emerald-400 text-left transition group"
            >
              <div className="font-semibold text-white text-xs flex items-center justify-between">
                <span>Certification Center (8 Steps)</span>
                <ArrowRight className="w-3.5 h-3.5 text-emerald-400 group-hover:translate-x-1 transition" />
              </div>
              <p className="text-[11px] text-gray-400 mt-1">
                Execute automated 8-step contract harness with mock vs real distinction.
              </p>
            </button>

            <button
              onClick={() => onNavigate('import')}
              id="quick-action-import"
              className="p-3.5 rounded-lg bg-gradient-to-br from-purple-900/40 to-pink-900/40 border border-purple-500/30 hover:border-purple-400 text-left transition group"
            >
              <div className="font-semibold text-white text-xs flex items-center justify-between">
                <span>Catalogue CSV Importer</span>
                <ArrowRight className="w-3.5 h-3.5 text-purple-400 group-hover:translate-x-1 transition" />
              </div>
              <p className="text-[11px] text-gray-400 mt-1">
                Import 1,000+ rows with normalization, duplicate detection, and progress jobs.
              </p>
            </button>

            <button
              onClick={() => onNavigate('rules')}
              id="quick-action-rules"
              className="p-3.5 rounded-lg bg-gradient-to-br from-amber-900/40 to-orange-900/40 border border-amber-500/30 hover:border-amber-400 text-left transition group"
            >
              <div className="font-semibold text-white text-xs flex items-center justify-between">
                <span>AI Rule Capture Adapter</span>
                <ArrowRight className="w-3.5 h-3.5 text-amber-400 group-hover:translate-x-1 transition" />
              </div>
              <p className="text-[11px] text-gray-400 mt-1">
                Propose posting rules from community guidelines with human operator confirmation.
              </p>
            </button>
          </div>
        </div>
      </div>

      {/* Recent Jobs & Activity Stream */}
      <div className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Clock className="w-4 h-4 text-sky-400" />
            <span>Recent Durable Jobs & Platform Activity</span>
          </h3>
          <button
            onClick={() => onNavigate('jobs')}
            className="text-xs text-sky-400 hover:text-sky-300 font-medium"
          >
            View all jobs ({jobs.length}) →
          </button>
        </div>

        {jobs.length === 0 ? (
          <div className="text-center py-8 text-gray-400 text-xs">
            No durable background jobs recorded yet. Publish a post to generate the first job!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-gray-300">
              <thead className="bg-gray-800/60 text-gray-400 uppercase font-mono text-[10px]">
                <tr>
                  <th className="py-2.5 px-3">Job ID</th>
                  <th className="py-2.5 px-3">Idempotency Key</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Progress</th>
                  <th className="py-2.5 px-3">Result Link</th>
                  <th className="py-2.5 px-3">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60 font-mono text-[11px]">
                {jobs.slice(0, 6).map((job) => (
                  <tr key={job.job_id} className="hover:bg-gray-800/40">
                    <td className="py-2.5 px-3 font-semibold text-sky-400">{job.job_id}</td>
                    <td className="py-2.5 px-3 text-gray-400 truncate max-w-[140px]">{job.idempotency_key || '—'}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          job.status === 'succeeded'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : job.status === 'failed'
                            ? 'bg-red-500/20 text-red-400'
                            : 'bg-amber-500/20 text-amber-400 animate-pulse'
                        }`}
                      >
                        {job.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="w-24 bg-gray-800 rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-full ${
                            job.status === 'succeeded'
                              ? 'bg-emerald-500'
                              : job.status === 'failed'
                              ? 'bg-red-500'
                              : 'bg-sky-500'
                          }`}
                          style={{ width: `${job.progress}%` }}
                        ></div>
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      {job.result_links?.live_url ? (
                        <a
                          href={job.result_links.live_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-sky-400 hover:underline truncate block max-w-[150px]"
                        >
                          {job.result_links.live_url}
                        </a>
                      ) : (
                        <span className="text-gray-400">None</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-gray-400">
                      {new Date(job.created_at).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
