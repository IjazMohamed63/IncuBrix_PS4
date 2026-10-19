import React, { useEffect, useState } from 'react';
import {
  Send,
  Sparkles,
  ShieldAlert,
  CheckCircle2,
  AlertOctagon,
  Clock,
  ExternalLink,
  RefreshCw,
  FileCode2,
  Copy,
  ChevronDown,
  Layers,
  Check,
} from 'lucide-react';
import { api } from '../api/client';
import { Destination, Rendition, RuleDecision } from '../types';

interface PublishPageProps {
  initialDestinationId?: string;
}

export const PublishPage: React.FC<PublishPageProps> = ({ initialDestinationId }) => {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [selectedDestId, setSelectedDestId] = useState<string>(initialDestinationId || '');

  // Form Fields
  const [title, setTitle] = useState<string>(
    'Building Scalable AI Agent Architectures: Lessons Learned in Production'
  );
  const [body, setBody] = useState<string>(
    'We explored asynchronous durable background execution, automated certification harnesses, and pre-flight posting rules. What are the key bottlenecks your teams are experiencing when deploying autonomous agents?'
  );
  const [canonicalUrl, setCanonicalUrl] = useState<string>('https://incubrix.io/blog/scalable-ai-agents');
  const [tagsInput, setTagsInput] = useState<string>('ai, machine-learning, systems, architecture');
  const [aiDisclosure, setAiDisclosure] = useState<boolean>(true);
  const [isPromotional, setIsPromotional] = useState<boolean>(false);
  const [idempotencyKey, setIdempotencyKey] = useState<string>(
    () => `pub_key_${Math.random().toString(36).substring(2, 10)}`
  );

  // Pre-flight & Tailoring state
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [ruleDecision, setRuleDecision] = useState<RuleDecision | null>(null);
  const [tailoredPreview, setTailoredPreview] = useState<{
    tailored_rendition: Rendition;
    modifications: string[];
  } | null>(null);

  // Publishing & Job Tracking state
  const [publishing, setPublishing] = useState<boolean>(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobProgress, setJobProgress] = useState<number>(0);
  const [jobStatus, setJobStatus] = useState<string>('');
  const [jobResult, setJobResult] = useState<any | null>(null);
  const [showManifest, setShowManifest] = useState<boolean>(false);

  useEffect(() => {
    api.getDestinations().then((dests) => {
      setDestinations(dests);
      if (!selectedDestId && dests.length > 0) {
        // Pick first automated destination
        const automated = dests.find((d) => d.automation_allowed) || dests[0];
        setSelectedDestId(automated.id);
      }
    });
  }, []);

  const getRendition = (): Rendition => {
    const tags = tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    return {
      title,
      body,
      canonical_url: canonicalUrl || undefined,
      tags,
      media: [],
      ai_disclosure: aiDisclosure
        ? 'AI Disclosure: Content researched and drafted with AI assistance.'
        : undefined,
      custom_fields: {
        is_promotional: isPromotional,
      },
    };
  };

  const handleEvaluateAndTailor = async () => {
    if (!selectedDestId) return;
    setEvaluating(true);
    try {
      const rendition = getRendition();
      const [decision, tailorRes] = await Promise.all([
        api.evaluateRules(selectedDestId, rendition),
        api.tailorRendition(selectedDestId, rendition),
      ]);
      setRuleDecision(decision);
      setTailoredPreview(tailorRes);
    } catch (err: any) {
      console.error('Evaluation failed:', err);
    } finally {
      setEvaluating(false);
    }
  };

  useEffect(() => {
    if (selectedDestId) {
      handleEvaluateAndTailor();
    }
  }, [selectedDestId, aiDisclosure, isPromotional]);

  const handlePublish = async () => {
    if (!selectedDestId) return;
    setPublishing(true);
    setJobResult(null);
    setJobProgress(10);
    setJobStatus('queued');

    try {
      const rendition = getRendition();
      const res = await api.publishContent(
        {
          rendition,
          destination_ids: [selectedDestId],
          async_mode: true,
        },
        idempotencyKey
      );

      const jId = res.job_id;
      setActiveJobId(jId);

      // Poll job status until complete
      const pollInterval = setInterval(async () => {
        try {
          const job = await api.getJob(jId);
          setJobProgress(job.progress);
          setJobStatus(job.status);
          if (job.status === 'succeeded' || job.status === 'failed') {
            clearInterval(pollInterval);
            setPublishing(false);
            setJobResult(job);
          }
        } catch {
          // ignore transient poll error
        }
      }, 700);
    } catch (err: any) {
      setPublishing(false);
      alert(`Publish failed: ${err.message}`);
    }
  };

  const selectedDest = destinations.find((d) => d.id === selectedDestId);

  return (
    <div id="page-publish" className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800 pb-5">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <span>Content Publishing & Distribution Dispatch</span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Surface-specific tailoring, pre-flight compliance rules, idempotency verification, and durable job tracking.
          </p>
        </div>

        <button
          onClick={handleEvaluateAndTailor}
          id="re-evaluate-rules-btn"
          disabled={evaluating}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-medium border border-gray-700 transition self-start"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${evaluating ? 'animate-spin text-sky-400' : ''}`} />
          <span>Re-Evaluate Rules</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Content Composer */}
        <div className="lg:col-span-7 space-y-4">
          <div className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-4">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Send className="w-4 h-4 text-sky-400" />
              <span>Universal Content Composer</span>
            </h2>

            {/* Destination Target Selector */}
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1">Target Catalogue Destination</label>
              <select
                id="publish-destination-select"
                value={selectedDestId}
                onChange={(e) => setSelectedDestId(e.target.value)}
                className="w-full bg-gray-800/90 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
              >
                {destinations.map((d) => (
                  <option key={d.id} value={d.id}>
                    [{d.platform_key.toUpperCase()}] {d.name} ({d.surface}) - Level: {d.level}
                  </option>
                ))}
              </select>
              {selectedDest && (
                <div className="mt-1 flex items-center gap-2 text-[11px] text-gray-400 font-mono">
                  <span>Surface: {selectedDest.surface}</span>
                  <span>•</span>
                  <span>Max Title: {selectedDest.parameters?.title_max_chars || 'None'}</span>
                  <span>•</span>
                  <span>
                    Auto: {selectedDest.automation_allowed ? 'Direct Bot' : 'Assisted Pack Required'}
                  </span>
                </div>
              )}
            </div>

            {/* Title */}
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1">Post Title</label>
              <input
                type="text"
                id="publish-title-input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full bg-gray-800/90 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-500"
              />
              <div className="text-[10px] text-gray-400 mt-1 font-mono text-right">{title.length} characters</div>
            </div>

            {/* Body */}
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1">Post Body</label>
              <textarea
                id="publish-body-input"
                rows={5}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                className="w-full bg-gray-800/90 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
              />
              <div className="text-[10px] text-gray-400 mt-1 font-mono text-right">{body.length} characters</div>
            </div>

            {/* Canonical URL & Tags */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">Canonical URL</label>
                <input
                  type="text"
                  id="publish-canonical-url-input"
                  value={canonicalUrl}
                  onChange={(e) => setCanonicalUrl(e.target.value)}
                  className="w-full bg-gray-800/90 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">Audience Tags (comma separated)</label>
                <input
                  type="text"
                  id="publish-tags-input"
                  value={tagsInput}
                  onChange={(e) => setTagsInput(e.target.value)}
                  className="w-full bg-gray-800/90 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
                />
              </div>
            </div>

            {/* Compliance Toggles */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              <label className="flex items-center space-x-2 p-2.5 rounded-lg bg-gray-800/50 border border-gray-800 cursor-pointer text-xs">
                <input
                  type="checkbox"
                  id="publish-ai-disclosure-checkbox"
                  checked={aiDisclosure}
                  onChange={(e) => setAiDisclosure(e.target.checked)}
                  className="rounded bg-gray-700 text-sky-500 focus:ring-0"
                />
                <span className="text-gray-300 font-medium">Include AI Disclosure Tag</span>
              </label>

              <label className="flex items-center space-x-2 p-2.5 rounded-lg bg-gray-800/50 border border-gray-800 cursor-pointer text-xs">
                <input
                  type="checkbox"
                  id="publish-promotional-checkbox"
                  checked={isPromotional}
                  onChange={(e) => setIsPromotional(e.target.checked)}
                  className="rounded bg-gray-700 text-amber-500 focus:ring-0"
                />
                <span className="text-gray-300 font-medium">Flag as Commercial / Promotional</span>
              </label>
            </div>

            {/* Idempotency Key & Dispatch Button */}
            <div className="pt-3 border-t border-gray-800 space-y-3">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-gray-300">Idempotency-Key Header</label>
                  <button
                    onClick={() => setIdempotencyKey(`pub_key_${Math.random().toString(36).substring(2, 10)}`)}
                    className="text-[11px] text-sky-400 hover:underline flex items-center gap-1"
                  >
                    <RefreshCw className="w-2.5 h-2.5" /> Regenerate
                  </button>
                </div>
                <input
                  type="text"
                  id="publish-idempotency-key-input"
                  value={idempotencyKey}
                  onChange={(e) => setIdempotencyKey(e.target.value)}
                  className="w-full bg-gray-800/90 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-sky-500"
                />
              </div>

              <button
                onClick={handlePublish}
                disabled={publishing || ruleDecision?.action === 'block'}
                id="publish-submit-btn"
                className={`w-full py-3 px-4 rounded-xl font-bold text-xs flex items-center justify-center space-x-2 transition shadow-md ${
                  ruleDecision?.action === 'block'
                    ? 'bg-red-950/60 text-red-300 border border-red-500/40 cursor-not-allowed'
                    : publishing
                    ? 'bg-sky-600/70 text-sky-200 cursor-wait'
                    : 'bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white'
                }`}
              >
                <Send className={`w-4 h-4 ${publishing ? 'animate-bounce' : ''}`} />
                <span>
                  {publishing
                    ? 'Dispatching Background Job...'
                    : ruleDecision?.action === 'block'
                    ? 'Blocked by Pre-Flight Rules (Resolve Below)'
                    : 'Dispatch Publication Job'}
                </span>
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Pre-Flight Rule Decision & Tailored Preview */}
        <div className="lg:col-span-5 space-y-4">
          {/* Rule Decision Card */}
          <div className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              <span>Pre-Flight Rules Decision</span>
            </h3>

            {evaluating ? (
              <div className="py-6 text-center text-xs text-gray-400 flex items-center justify-center space-x-2">
                <RefreshCw className="w-4 h-4 animate-spin text-sky-400" />
                <span>Evaluating destination rules...</span>
              </div>
            ) : ruleDecision ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400 font-mono">Decision:</span>
                  <span
                    id="rule-decision-badge"
                    className={`px-2.5 py-1 rounded-md text-xs font-mono font-bold uppercase tracking-wider border ${
                      ruleDecision.action === 'allow'
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                        : ruleDecision.action === 'block'
                        ? 'bg-red-500/20 text-red-300 border-red-500/40 animate-pulse'
                        : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    }`}
                  >
                    {ruleDecision.action}
                  </span>
                </div>

                {ruleDecision.rule && (
                  <div className="text-xs font-mono text-gray-300">
                    Rule Violated: <span className="text-red-400 font-bold">{ruleDecision.rule}</span>
                  </div>
                )}

                <div
                  id="rule-decision-reason"
                  className={`p-3 rounded-lg text-xs border ${
                    ruleDecision.action === 'allow'
                      ? 'bg-emerald-950/30 text-emerald-200 border-emerald-500/30'
                      : 'bg-red-950/30 text-red-200 border-red-500/30'
                  }`}
                >
                  <div className="font-semibold mb-0.5">Evaluation Reason:</div>
                  <div>{ruleDecision.reason}</div>
                </div>

                {ruleDecision.required_human_action && (
                  <div
                    id="rule-blocked-reason"
                    className="p-3 rounded-lg bg-amber-950/30 text-amber-200 border border-amber-500/30 text-xs"
                  >
                    <div className="font-bold flex items-center gap-1 text-amber-300 mb-0.5">
                      <AlertOctagon className="w-3.5 h-3.5" /> Required Human Action:
                    </div>
                    <div>{ruleDecision.required_human_action}</div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-xs text-gray-400 py-4 text-center">Select a destination to evaluate.</div>
            )}
          </div>

          {/* Tailored Renditions Preview */}
          <div className="p-5 rounded-xl bg-gray-900/70 border border-gray-800 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-sky-400" />
              <span>Tailored Rendition Preview</span>
            </h3>

            {tailoredPreview ? (
              <div className="space-y-3 text-xs">
                {tailoredPreview.modifications.length > 0 && (
                  <div className="p-2.5 rounded-lg bg-sky-950/30 border border-sky-500/30 text-sky-200">
                    <div className="font-bold text-[11px] mb-1">Applied Tailoring Rules:</div>
                    <ul className="list-disc pl-4 space-y-0.5 text-[11px]">
                      {tailoredPreview.modifications.map((m, idx) => (
                        <li key={idx}>{m}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="p-3 rounded-lg bg-black/40 border border-gray-800 space-y-2">
                  <div>
                    <div className="text-[10px] uppercase font-mono text-gray-400">Tailored Title:</div>
                    <div className="font-bold text-gray-200 text-xs">{tailoredPreview.tailored_rendition.title}</div>
                  </div>

                  <div>
                    <div className="text-[10px] uppercase font-mono text-gray-400">Tailored Body:</div>
                    <div className="text-gray-300 text-[11px] font-mono whitespace-pre-wrap max-h-36 overflow-y-auto">
                      {tailoredPreview.tailored_rendition.body}
                    </div>
                  </div>

                  {tailoredPreview.tailored_rendition.tags && tailoredPreview.tailored_rendition.tags.length > 0 && (
                    <div>
                      <div className="text-[10px] uppercase font-mono text-gray-400">Adapted Hashtags:</div>
                      <div className="flex flex-wrap gap-1 mt-0.5">
                        {tailoredPreview.tailored_rendition.tags.map((t, idx) => (
                          <span key={idx} className="px-1.5 py-0.5 rounded bg-gray-800 text-sky-400 font-mono text-[10px]">
                            #{t}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-xs text-gray-400 py-4 text-center">No preview available.</div>
            )}
          </div>

          {/* Real-time Job Progress & Tracker */}
          {activeJobId && (
            <div id="job-tracker-card" className="p-5 rounded-xl bg-gray-900 border border-sky-500/40 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-white uppercase font-mono flex items-center gap-2">
                  <FileCode2 className="w-4 h-4 text-sky-400" />
                  <span>Durable Background Job Tracking</span>
                </h3>
                <span
                  id="active-job-status-badge"
                  className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
                    jobStatus === 'succeeded'
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : jobStatus === 'failed'
                      ? 'bg-red-500/20 text-red-400'
                      : 'bg-sky-500/20 text-sky-400 animate-pulse'
                  }`}
                >
                  {jobStatus.toUpperCase()} ({jobProgress}%)
                </span>
              </div>

              <div className="text-xs font-mono text-gray-300">
                Job ID: <span className="text-sky-400 font-bold">{activeJobId}</span>
              </div>

              <div className="w-full bg-gray-800 rounded-full h-2.5 overflow-hidden">
                <div
                  id="active-job-progress-bar"
                  className={`h-full transition-all duration-300 ${
                    jobStatus === 'succeeded'
                      ? 'bg-emerald-500'
                      : jobStatus === 'failed'
                      ? 'bg-red-500'
                      : 'bg-sky-500'
                  }`}
                  style={{ width: `${jobProgress}%` }}
                ></div>
              </div>

              {jobResult && (
                <div className="space-y-2 pt-2 text-xs">
                  {jobResult.result_links?.live_url && (
                    <div className="p-2.5 rounded bg-emerald-950/40 border border-emerald-500/30 text-emerald-200">
                      <div className="font-bold text-[11px] mb-0.5">Published Live URL:</div>
                      <a
                        href={jobResult.result_links.live_url}
                        target="_blank"
                        rel="noreferrer"
                        id="published-live-url-link"
                        className="text-sky-300 hover:underline font-mono truncate block flex items-center gap-1"
                      >
                        <span>{jobResult.result_links.live_url}</span>
                        <ExternalLink className="w-3 h-3 shrink-0" />
                      </a>
                    </div>
                  )}

                  <button
                    onClick={() => setShowManifest(!showManifest)}
                    className="text-sky-400 hover:underline text-[11px] font-mono"
                  >
                    {showManifest ? 'Hide Output Manifest JSON' : 'View Output Manifest JSON'}
                  </button>

                  {showManifest && (
                    <pre className="bg-black/60 p-2.5 rounded border border-gray-800 text-[10px] font-mono text-gray-300 max-h-40 overflow-y-auto">
                      {JSON.stringify(jobResult.manifest || jobResult, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
