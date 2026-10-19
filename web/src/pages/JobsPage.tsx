import React, { useEffect, useState } from 'react';
import {
  FileCode2,
  Clock,
  ExternalLink,
  RefreshCw,
  Search,
  CheckCircle2,
  AlertTriangle,
  X,
  Code2,
  Fingerprint,
  Link2,
} from 'lucide-react';
import { api } from '../api/client';
import { JobRecord } from '../types';

export const JobsPage: React.FC = () => {
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedJob, setSelectedJob] = useState<JobRecord | null>(null);
  const [search, setSearch] = useState<string>('');

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const data = await api.getJobs(100);
      setJobs(data);
    } catch (err: any) {
      console.error('Failed to load jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const filteredJobs = jobs.filter((j) => {
    const s = search.toLowerCase();
    return (
      j.job_id.toLowerCase().includes(s) ||
      (j.idempotency_key && j.idempotency_key.toLowerCase().includes(s)) ||
      j.status.toLowerCase().includes(s)
    );
  });

  return (
    <div id="page-jobs" className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800 pb-5">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <span>Durable Background Jobs & Structured Execution Logs</span>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              {jobs.length} Total
            </span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Persisted SQLite disk logs surviving API restarts, HMAC-signed callbacks, and full output manifest audit JSON.
          </p>
        </div>

        <button
          onClick={fetchJobs}
          id="refresh-jobs-btn"
          disabled={loading}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-medium border border-gray-700 transition self-start"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
          <span>Refresh Jobs</span>
        </button>
      </div>

      {/* Search Input */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
        <input
          type="text"
          id="jobs-search-input"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter by Job ID, Idempotency-Key, status..."
          className="w-full bg-gray-900 border border-gray-700 rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-sky-500 font-mono"
        />
      </div>

      {/* Jobs Table */}
      <div className="rounded-xl border border-gray-800 bg-gray-900/60 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-gray-300">
            <thead className="bg-gray-800/80 text-gray-400 uppercase font-mono text-[10px] border-b border-gray-800">
              <tr>
                <th className="py-3 px-4">Job ID</th>
                <th className="py-3 px-4">Idempotency Key</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Progress</th>
                <th className="py-3 px-4">Live Result Link</th>
                <th className="py-3 px-4">Created At</th>
                <th className="py-3 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 font-mono text-[11px]">
              {filteredJobs.map((job) => (
                <tr
                  key={job.job_id}
                  id={`job-row-${job.job_id}`}
                  className="hover:bg-gray-800/40 transition group"
                >
                  <td className="py-3 px-4 font-bold text-sky-400">{job.job_id}</td>
                  <td className="py-3 px-4 text-gray-400 truncate max-w-[150px]">
                    {job.idempotency_key || '—'}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        job.status === 'succeeded'
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : job.status === 'failed'
                          ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                          : 'bg-amber-500/20 text-amber-400 border border-amber-500/30 animate-pulse'
                      }`}
                    >
                      {job.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center space-x-2">
                      <div className="w-20 bg-gray-800 rounded-full h-2 overflow-hidden">
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
                      <span className="text-[10px] text-gray-400">{job.progress}%</span>
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    {job.result_links?.live_url ? (
                      <a
                        href={job.result_links.live_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-sky-400 hover:underline truncate block max-w-[180px] flex items-center gap-1"
                      >
                        <span className="truncate">{job.result_links.live_url}</span>
                        <ExternalLink className="w-2.5 h-2.5 shrink-0" />
                      </a>
                    ) : (
                      <span className="text-gray-500">None</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-gray-400">
                    {new Date(job.created_at).toLocaleTimeString()}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => setSelectedJob(job)}
                      id={`inspect-job-btn-${job.job_id}`}
                      className="p-1 px-2.5 rounded bg-gray-800 hover:bg-gray-700 text-sky-400 hover:text-sky-300 font-sans text-xs transition border border-gray-700"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Job Details Drawer */}
      {selectedJob && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex justify-end animate-in fade-in">
          <div className="w-full max-w-2xl bg-[#0e1424] border-l border-gray-800 h-full p-6 overflow-y-auto space-y-6 shadow-2xl">
            <div className="flex items-start justify-between border-b border-gray-800 pb-4">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-mono font-bold text-sky-400">{selectedJob.job_id}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                      selectedJob.status === 'succeeded'
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : selectedJob.status === 'failed'
                        ? 'bg-red-500/20 text-red-400'
                        : 'bg-amber-500/20 text-amber-400'
                    }`}
                  >
                    {selectedJob.status.toUpperCase()} ({selectedJob.progress}%)
                  </span>
                </div>
                <h2 className="text-base font-bold text-white mt-1">Durable Job Audit Telemetry</h2>
              </div>

              <button
                onClick={() => setSelectedJob(null)}
                className="p-1 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Idempotency & Replay Protection */}
            <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-2 text-xs font-mono">
              <div className="flex items-center space-x-2 text-indigo-400 font-bold">
                <Fingerprint className="w-4 h-4" />
                <span>Idempotency Key & Execution Context</span>
              </div>
              <div className="bg-black/40 p-2.5 rounded border border-gray-800 text-gray-300">
                <div>Key: {selectedJob.idempotency_key || 'None provided'}</div>
                <div className="text-gray-400 text-[11px] mt-1">
                  Replays with the same idempotency key and body return this identical job record without duplicating external platform posts.
                </div>
              </div>
            </div>

            {/* Timings & Results */}
            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-3 rounded-lg bg-gray-900 border border-gray-800">
                <div className="text-gray-400 text-[10px]">Created</div>
                <div className="text-gray-200 mt-1">{new Date(selectedJob.created_at).toLocaleString()}</div>
              </div>
              <div className="p-3 rounded-lg bg-gray-900 border border-gray-800">
                <div className="text-gray-400 text-[10px]">Updated</div>
                <div className="text-gray-200 mt-1">{new Date(selectedJob.updated_at).toLocaleString()}</div>
              </div>
            </div>

            {/* Error Message if Failed */}
            {selectedJob.error_message && (
              <div className="p-3.5 rounded-lg bg-red-950/40 border border-red-500/40 text-xs text-red-200 font-mono">
                <div className="font-bold text-red-300 mb-1">Execution Failure:</div>
                <div>{selectedJob.error_message}</div>
              </div>
            )}

            {/* Manifest JSON */}
            <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-gray-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Code2 className="w-4 h-4 text-sky-400" />
                  <span>Output Manifest JSON</span>
                </h3>
              </div>
              <pre className="bg-black/60 p-3 rounded-lg border border-gray-800 text-[11px] font-mono text-gray-300 overflow-x-auto max-h-72">
                {JSON.stringify(selectedJob.manifest || selectedJob.result || selectedJob, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
