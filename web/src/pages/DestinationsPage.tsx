import React, { useEffect, useState } from 'react';
import {
  Search,
  Filter,
  MapPin,
  ExternalLink,
  ShieldCheck,
  Star,
  Award,
  ChevronRight,
  X,
  Play,
  Clock,
  Sparkles,
  RefreshCw,
} from 'lucide-react';
import { api } from '../api/client';
import { Destination } from '../types';

interface DestinationsPageProps {
  onNavigateToCertify?: (destinationId: string) => void;
  onNavigateToPublish?: (destinationId: string) => void;
}

export const DestinationsPage: React.FC<DestinationsPageProps> = ({
  onNavigateToCertify,
  onNavigateToPublish,
}) => {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedPlatform, setSelectedPlatform] = useState<string>('all');
  const [selectedLevel, setSelectedLevel] = useState<string>('all');
  const [selectedDestination, setSelectedDestination] = useState<Destination | null>(null);

  // Certification trigger state
  const [certifyingId, setCertifyingId] = useState<string | null>(null);
  const [certResult, setCertResult] = useState<any | null>(null);

  const fetchDestinations = async () => {
    setLoading(true);
    try {
      const data = await api.getDestinations();
      setDestinations(data);
    } catch (err: any) {
      console.error('Failed to load destinations:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDestinations();
  }, []);

  const handleRunCertification = async (destId: string, isMock: boolean = true) => {
    setCertifyingId(destId);
    try {
      const res = await api.runCertification(destId, isMock);
      setCertResult(res);
      // Refresh list to update level
      await fetchDestinations();
      if (selectedDestination?.id === destId) {
        setSelectedDestination((prev) => (prev ? { ...prev, level: res.assigned_level } : null));
      }
    } catch (err: any) {
      alert(`Certification failed: ${err.message}`);
    } finally {
      setCertifyingId(null);
    }
  };

  // Filtering
  const filtered = destinations.filter((dest) => {
    const matchSearch =
      dest.name.toLowerCase().includes(search.toLowerCase()) ||
      dest.url.toLowerCase().includes(search.toLowerCase()) ||
      dest.platform_key.toLowerCase().includes(search.toLowerCase()) ||
      (dest.audience_tags && dest.audience_tags.some((t) => t.toLowerCase().includes(search.toLowerCase())));

    const matchCategory = selectedCategory === 'all' || dest.category === selectedCategory;
    const matchPlatform = selectedPlatform === 'all' || dest.platform_key === selectedPlatform;
    const matchLevel = selectedLevel === 'all' || dest.level === selectedLevel;

    return matchSearch && matchCategory && matchPlatform && matchLevel;
  });

  const categories = Array.from(new Set(destinations.map((d) => d.category))).filter(Boolean);
  const platforms = Array.from(new Set(destinations.map((d) => d.platform_key))).filter(Boolean);

  return (
    <div id="page-destinations" className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800 pb-5">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <span>Destination Catalogue Explorer</span>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30">
              {destinations.length} Rows
            </span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Browse, search, and inspect long-tail platforms with explainable 1-5 relevance scores and direct 8-step certification.
          </p>
        </div>

        <button
          onClick={fetchDestinations}
          id="refresh-destinations-btn"
          disabled={loading}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-medium border border-gray-700 transition self-start"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Search & Filter Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 bg-gray-900/60 p-4 rounded-xl border border-gray-800">
        <div className="relative md:col-span-1">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
          <input
            type="text"
            id="destination-search-input"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search destination name, URL, tag..."
            className="w-full bg-gray-800/80 border border-gray-700 rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-sky-500 transition"
          />
        </div>

        <div>
          <select
            id="destination-category-filter"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-500"
          >
            <option value="all">All Categories ({categories.length})</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                Category: {c.toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        <div>
          <select
            id="destination-platform-filter"
            value={selectedPlatform}
            onChange={(e) => setSelectedPlatform(e.target.value)}
            className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-500"
          >
            <option value="all">All Platforms ({platforms.length})</option>
            {platforms.map((p) => (
              <option key={p} value={p}>
                Platform: {p}
              </option>
            ))}
          </select>
        </div>

        <div>
          <select
            id="destination-level-filter"
            value={selectedLevel}
            onChange={(e) => setSelectedLevel(e.target.value)}
            className="w-full bg-gray-800/80 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-500"
          >
            <option value="all">All Certification Levels</option>
            <option value="L0">L0 (Demoted / Uncertified)</option>
            <option value="L1">L1 (Contract Certified)</option>
            <option value="L2">L2 (Production Active)</option>
            <option value="L3">L3 (High Throughput)</option>
          </select>
        </div>
      </div>

      {/* Destinations Table */}
      <div className="rounded-xl border border-gray-800 bg-gray-900/60 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-gray-300">
            <thead className="bg-gray-800/80 text-gray-400 uppercase font-mono text-[10px] border-b border-gray-800">
              <tr>
                <th className="py-3 px-4">Destination & URL</th>
                <th className="py-3 px-4">Platform & Surface</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Relevance</th>
                <th className="py-3 px-4">Est. Reach</th>
                <th className="py-3 px-4">Level</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 font-sans">
              {filtered.map((dest) => (
                <tr
                  key={dest.id}
                  id={`destination-row-${dest.id}`}
                  className="hover:bg-gray-800/40 transition group"
                >
                  <td className="py-3 px-4">
                    <div className="font-semibold text-white group-hover:text-sky-300 transition flex items-center gap-1.5">
                      <span>{dest.name}</span>
                    </div>
                    <a
                      href={dest.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[11px] text-gray-400 hover:text-sky-400 flex items-center gap-1 font-mono mt-0.5 truncate max-w-xs"
                    >
                      <span>{dest.url}</span>
                      <ExternalLink className="w-2.5 h-2.5 shrink-0" />
                    </a>
                  </td>

                  <td className="py-3 px-4 font-mono">
                    <div className="flex items-center gap-1.5">
                      <span className="px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-400 border border-indigo-500/30 text-[10px] uppercase font-bold">
                        {dest.platform_key}
                      </span>
                      <span className="text-gray-400 text-[11px]">{dest.surface}</span>
                    </div>
                  </td>

                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-300 text-[10px] uppercase font-medium">
                      {dest.category}
                    </span>
                  </td>

                  <td className="py-3 px-4">
                    <div className="flex items-center space-x-1" title={dest.relevance_reason || 'Relevance score'}>
                      {[1, 2, 3, 4, 5].map((star) => (
                        <Star
                          key={star}
                          className={`w-3 h-3 ${
                            star <= (dest.relevance_score || 3)
                              ? 'text-amber-400 fill-amber-400'
                              : 'text-gray-700'
                          }`}
                        />
                      ))}
                      <span className="text-[11px] font-mono text-gray-400 ml-1 font-semibold">
                        {dest.relevance_score || 3}/5
                      </span>
                    </div>
                  </td>

                  <td className="py-3 px-4 font-mono text-gray-300 text-[11px]">
                    {dest.est_audience ? dest.est_audience.toLocaleString() : '—'}
                  </td>

                  <td className="py-3 px-4">
                    <span
                      className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold border ${
                        dest.level === 'L0'
                          ? 'bg-red-500/15 text-red-400 border-red-500/30'
                          : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                      }`}
                    >
                      {dest.level || 'L0'}
                    </span>
                  </td>

                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <button
                        onClick={() => handleRunCertification(dest.id, true)}
                        disabled={certifyingId === dest.id}
                        id={`certify-btn-${dest.id}`}
                        title="Run 8-Step Certification Harness"
                        className="p-1.5 rounded-lg bg-gray-800 hover:bg-emerald-950 text-gray-300 hover:text-emerald-300 border border-gray-700 hover:border-emerald-500/40 text-[11px] transition flex items-center gap-1"
                      >
                        <Play className={`w-3 h-3 ${certifyingId === dest.id ? 'animate-spin text-emerald-400' : 'text-emerald-400'}`} />
                        <span>{certifyingId === dest.id ? 'Certifying...' : 'Certify'}</span>
                      </button>

                      <button
                        onClick={() => setSelectedDestination(dest)}
                        id={`detail-btn-${dest.id}`}
                        className="p-1.5 rounded-lg bg-gray-800 hover:bg-sky-950 text-gray-300 hover:text-sky-300 border border-gray-700 hover:border-sky-500/40 text-[11px] transition"
                      >
                        Details
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Destination Detail Modal / Drawer */}
      {selectedDestination && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex justify-end animate-in fade-in">
          <div className="w-full max-w-xl bg-[#0e1424] border-l border-gray-800 h-full p-6 overflow-y-auto space-y-6 shadow-2xl">
            {/* Header */}
            <div className="flex items-start justify-between border-b border-gray-800 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold border ${
                      selectedDestination.level === 'L0'
                        ? 'bg-red-500/20 text-red-400 border-red-500/30'
                        : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                    }`}
                  >
                    {selectedDestination.level || 'L0'}
                  </span>
                  <span className="text-xs font-mono uppercase text-indigo-400 px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20">
                    {selectedDestination.platform_key}
                  </span>
                </div>
                <h2 className="text-lg font-bold text-white mt-1.5">{selectedDestination.name}</h2>
                <a
                  href={selectedDestination.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-sky-400 font-mono flex items-center gap-1 hover:underline mt-0.5"
                >
                  <span>{selectedDestination.url}</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>

              <button
                onClick={() => setSelectedDestination(null)}
                id="close-destination-drawer"
                className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Quick Actions */}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => handleRunCertification(selectedDestination.id, true)}
                disabled={certifyingId === selectedDestination.id}
                id="drawer-run-certification-btn"
                className="flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition shadow-sm"
              >
                <Play className="w-3.5 h-3.5" />
                <span>{certifyingId === selectedDestination.id ? 'Running 8 Steps...' : 'Run 8-Step Certification (Mock)'}</span>
              </button>

              {onNavigateToPublish && (
                <button
                  onClick={() => onNavigateToPublish(selectedDestination.id)}
                  id="drawer-publish-btn"
                  className="flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold transition shadow-sm"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Publish to this Destination</span>
                </button>
              )}
            </div>

            {/* Certification Result Notification */}
            {certResult && certResult.destination_id === selectedDestination.id && (
              <div className="p-3.5 rounded-lg bg-gray-900 border border-emerald-500/40 space-y-2">
                <div className="flex items-center justify-between text-xs font-bold text-emerald-400">
                  <span>Certification Result: {certResult.status.toUpperCase()}</span>
                  <span className="font-mono">{certResult.assigned_level}</span>
                </div>
                <div className="text-[11px] text-gray-300">
                  Label: <span className="font-mono text-amber-300">{certResult.is_mock ? 'mock' : 'real'}</span> (Mock runs cannot grant real-certified levels)
                </div>
                {certResult.evidence_s3_url && (
                  <div className="text-[11px] text-gray-400 font-mono truncate">
                    Evidence: <span className="text-sky-400">{certResult.evidence_s3_url}</span>
                  </div>
                )}
              </div>
            )}

            {/* Policy & Community Rules Card */}
            <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-3">
              <h3 className="text-xs font-bold text-gray-200 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-amber-400" />
                <span>Configured Community Rules & Policies</span>
              </h3>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded bg-gray-800/60 border border-gray-800">
                  <div className="text-gray-400 text-[11px]">Frequency Cap</div>
                  <div className="font-semibold text-white font-mono">{selectedDestination.frequency_cap}h cooldown</div>
                </div>

                <div className="p-2.5 rounded bg-gray-800/60 border border-gray-800">
                  <div className="text-gray-400 text-[11px]">Self-Promotion</div>
                  <div className={`font-semibold ${selectedDestination.self_promo_allowed ? 'text-emerald-400' : 'text-red-400'}`}>
                    {selectedDestination.self_promo_allowed ? 'Allowed' : 'Strictly Forbidden'}
                  </div>
                </div>

                <div className="p-2.5 rounded bg-gray-800/60 border border-gray-800">
                  <div className="text-gray-400 text-[11px]">Link Policy</div>
                  <div className="font-semibold text-white uppercase font-mono">{selectedDestination.link_policy}</div>
                </div>

                <div className="p-2.5 rounded bg-gray-800/60 border border-gray-800">
                  <div className="text-gray-400 text-[11px]">AI Disclosure</div>
                  <div className={`font-semibold ${selectedDestination.disclosure_required ? 'text-amber-400' : 'text-gray-300'}`}>
                    {selectedDestination.disclosure_required ? 'Mandatory Tag' : 'Optional'}
                  </div>
                </div>

                <div className="p-2.5 rounded bg-gray-800/60 border border-gray-800 col-span-2">
                  <div className="text-gray-400 text-[11px]">Automation Permission</div>
                  <div className={`font-semibold ${selectedDestination.automation_allowed ? 'text-emerald-400' : 'text-purple-400'}`}>
                    {selectedDestination.automation_allowed ? 'Direct API Bot Allowed' : 'Assisted Workflow Pack Required'}
                  </div>
                </div>
              </div>
            </div>

            {/* Relevance & Audience */}
            <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-3">
              <h3 className="text-xs font-bold text-gray-200 uppercase tracking-wider flex items-center gap-1.5">
                <Star className="w-4 h-4 text-amber-400" />
                <span>Relevance & Audience Signals</span>
              </h3>

              <div className="text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Score:</span>
                  <span className="font-mono font-bold text-amber-400">{selectedDestination.relevance_score}/5</span>
                </div>
                <div className="text-gray-300 text-[11px] bg-gray-800/50 p-2.5 rounded border border-gray-800">
                  {selectedDestination.relevance_reason || 'High topical alignment with developer and AI audiences.'}
                </div>

                <div className="pt-2">
                  <div className="text-gray-400 text-[11px] mb-1">Audience Tags:</div>
                  <div className="flex flex-wrap gap-1.5">
                    {(selectedDestination.audience_tags || []).map((t, idx) => (
                      <span key={idx} className="px-2 py-0.5 rounded bg-gray-800 text-sky-400 font-mono text-[10px]">
                        #{t}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Raw JSON Parameters */}
            <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-2">
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Parameters Manifest</h3>
              <pre className="text-[11px] font-mono text-gray-300 bg-black/40 p-3 rounded-lg overflow-x-auto max-h-48 border border-gray-800">
                {JSON.stringify(selectedDestination.parameters, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
