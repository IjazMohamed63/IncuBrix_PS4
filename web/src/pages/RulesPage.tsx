import React, { useEffect, useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Search,
  Check,
  UserCheck,
  Info,
} from 'lucide-react';
import { api } from '../api/client';
import { Destination, RuleAudit } from '../types';

export const RulesPage: React.FC = () => {
  const [policies, setPolicies] = useState<Array<{ id: string; name: string; description: string; enforcement: string; default: string }>>([]);
  const [audits, setAudits] = useState<RuleAudit[]>([]);
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // AI Rule Capture state
  const [captureDestId, setCaptureDestId] = useState<string>('');
  const [rulesText, setRulesText] = useState<string>(
    '1. Commercial self-promotion, affiliate links, and coupons are strictly forbidden.\n2. All AI-generated content must explicitly declare its AI nature in the post.\n3. Please limit submissions to once every 24 hours per author.\n4. Only direct links to verified developer documentation are allowed.'
  );
  const [proposing, setProposing] = useState<boolean>(false);
  const [proposedRule, setProposedRule] = useState<any | null>(null);
  const [confirming, setConfirming] = useState<boolean>(false);
  const [confirmedSuccess, setConfirmedSuccess] = useState<boolean>(false);

  const fetchRulesData = async () => {
    setLoading(true);
    try {
      const [pols, auds, dests] = await Promise.all([
        api.getRulePolicies().catch(() => []),
        api.getRuleAudits().catch(() => []),
        api.getDestinations().catch(() => []),
      ]);
      setPolicies(pols);
      setAudits(auds);
      setDestinations(dests);
      if (dests.length > 0 && !captureDestId) {
        setCaptureDestId(dests[0].id);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRulesData();
  }, []);

  const handleProposeRules = async () => {
    if (!captureDestId || !rulesText.trim()) return;
    setProposing(true);
    setConfirmedSuccess(false);
    try {
      const res = await api.proposeRules(captureDestId, rulesText);
      setProposedRule(res);
    } catch (err: any) {
      alert(`Rule proposal failed: ${err.message}`);
    } finally {
      setProposing(false);
    }
  };

  const handleConfirmRules = async () => {
    if (!captureDestId || !proposedRule) return;
    setConfirming(true);
    try {
      await api.confirmRules(captureDestId, proposedRule.id, 'dashboard_operator');
      setConfirmedSuccess(true);
      await fetchRulesData();
    } catch (err: any) {
      alert(`Rule confirmation failed: ${err.message}`);
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div id="page-rules" className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800 pb-5">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <span>Pre-Flight Rules Engine & Policy Audits</span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Zero-bypass compliance gate, deterministic audit log, and AI-powered community guidelines capture with human sign-off.
          </p>
        </div>

        <button
          onClick={fetchRulesData}
          id="refresh-rules-btn"
          disabled={loading}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-medium border border-gray-700 transition self-start"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
          <span>Refresh Audits</span>
        </button>
      </div>

      {/* Interactive AI Rule Proposal & Human Confirmation */}
      <div className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span>AI Rule Capture Adapter & Human Confirmation</span>
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Extracts strict structured constraints from unformatted guidelines. A human operator must explicitly confirm before activation.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1">Target Destination</label>
              <select
                id="rule-capture-dest-select"
                value={captureDestId}
                onChange={(e) => setCaptureDestId(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
              >
                {destinations.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.platform_key})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1">Raw Community Guidelines / Policy Text</label>
              <textarea
                id="rule-capture-text-input"
                rows={4}
                value={rulesText}
                onChange={(e) => setRulesText(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-sky-500"
              />
            </div>

            <button
              onClick={handleProposeRules}
              disabled={proposing}
              id="propose-rules-btn"
              className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs flex items-center space-x-1.5 transition shadow"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{proposing ? 'Proposing Rules via AI Adapter...' : 'Propose Rules (AI Step)'}</span>
            </button>
          </div>

          {/* Proposal Review & Confirmation */}
          <div className="p-4 rounded-lg bg-black/40 border border-gray-800 flex flex-col justify-between">
            <div>
              <div className="text-xs font-bold text-gray-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                <span>Proposed Rule Specification</span>
                {proposedRule && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    Confidence: {Math.round((proposedRule.confidence_score || 0.95) * 100)}%
                  </span>
                )}
              </div>

              {proposedRule ? (
                <div className="space-y-2 text-xs font-mono">
                  <div className="p-2.5 rounded bg-gray-900 border border-gray-800 space-y-1">
                    <div className="text-gray-400">
                      Frequency Cap: <span className="text-white font-bold">{proposedRule.frequency_cap}h</span>
                    </div>
                    <div className="text-gray-400">
                      Self Promo Allowed: <span className={proposedRule.self_promo_allowed ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>
                        {proposedRule.self_promo_allowed ? 'true' : 'false'}
                      </span>
                    </div>
                    <div className="text-gray-400">
                      Link Policy: <span className="text-amber-400 font-bold uppercase">{proposedRule.link_policy}</span>
                    </div>
                    <div className="text-gray-400">
                      AI Disclosure Required: <span className={proposedRule.disclosure_required ? 'text-amber-400 font-bold' : 'text-gray-300 font-bold'}>
                        {proposedRule.disclosure_required ? 'true' : 'false'}
                      </span>
                    </div>
                    {proposedRule.explanation && (
                      <div className="text-gray-300 text-[11px] pt-1 font-sans border-t border-gray-800">
                        {proposedRule.explanation}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-xs text-gray-500 py-8 text-center">
                  Click "Propose Rules" to extract structured community policies.
                </div>
              )}
            </div>

            {proposedRule && (
              <div className="pt-3 border-t border-gray-800 mt-3 flex items-center justify-between">
                {confirmedSuccess ? (
                  <div className="flex items-center space-x-1.5 text-xs text-emerald-400 font-bold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>Rules Confirmed & Activated!</span>
                  </div>
                ) : (
                  <button
                    onClick={handleConfirmRules}
                    disabled={confirming}
                    id="confirm-rules-btn"
                    className="w-full py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center justify-center space-x-1.5 transition shadow"
                  >
                    <UserCheck className="w-3.5 h-3.5" />
                    <span>{confirming ? 'Confirming...' : 'Human Confirmation: Activate Rules'}</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Configured Posting Policies */}
      <div className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-4">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-sky-400" />
          <span>Deterministic Posting Policies Enforced</span>
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {policies.map((p) => (
            <div key={p.id} className="p-3.5 rounded-lg bg-gray-800/40 border border-gray-800 space-y-1.5 text-xs">
              <div className="font-bold text-sky-300">{p.name}</div>
              <p className="text-[11px] text-gray-400 leading-relaxed">{p.description}</p>
              <div className="pt-1 text-[10px] font-mono text-gray-300 bg-gray-900/60 p-1.5 rounded border border-gray-800">
                {p.enforcement}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pre-Flight Rule Audit Records Table */}
      <div className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Info className="w-4 h-4 text-indigo-400" />
            <span>Pre-Flight Rules Audit Trail ({audits.length} Records)</span>
          </h2>
          <span className="text-xs text-gray-400 font-mono">Provable pre-connector enforcement</span>
        </div>

        {audits.length === 0 ? (
          <div className="text-center py-8 text-gray-500 text-xs">
            No pre-flight rule evaluations recorded yet. Publish or evaluate a post to record decisions.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-gray-300">
              <thead className="bg-gray-800/80 text-gray-400 uppercase font-mono text-[10px]">
                <tr>
                  <th className="py-2.5 px-3">Decision</th>
                  <th className="py-2.5 px-3">Destination</th>
                  <th className="py-2.5 px-3">Rule Violated</th>
                  <th className="py-2.5 px-3">Evaluation Reason</th>
                  <th className="py-2.5 px-3">Required Human Action</th>
                  <th className="py-2.5 px-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60 font-sans text-[11px]">
                {audits.map((a) => (
                  <tr key={a.id} className="hover:bg-gray-800/40">
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold uppercase ${
                          a.decision === 'allow'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : a.decision === 'block'
                            ? 'bg-red-500/20 text-red-400'
                            : 'bg-amber-500/20 text-amber-400'
                        }`}
                      >
                        {a.decision}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-gray-300">{a.destination_id}</td>
                    <td className="py-2.5 px-3 font-mono font-bold text-amber-400">{a.rule_violated || 'None'}</td>
                    <td className="py-2.5 px-3 text-gray-300 max-w-xs">{a.reason}</td>
                    <td className="py-2.5 px-3 text-gray-400 max-w-xs">{a.human_action_required || 'None'}</td>
                    <td className="py-2.5 px-3 text-gray-400 font-mono">
                      {a.timestamp ? new Date(a.timestamp).toLocaleTimeString() : '—'}
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
