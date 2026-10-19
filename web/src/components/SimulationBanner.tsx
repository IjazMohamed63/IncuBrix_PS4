import React, { useEffect, useState } from 'react';
import { AlertTriangle, ShieldCheck, Zap, ToggleLeft, ToggleRight } from 'lucide-react';
import { api } from '../api/client';

export const SimulationBanner: React.FC = () => {
  const [simulationMode, setSimulationMode] = useState<boolean>(true);
  const [tokenStatus, setTokenStatus] = useState<string>('active');
  const [rateLimit, setRateLimit] = useState<{ remaining: number; limit: number }>({ remaining: 118, limit: 120 });

  useEffect(() => {
    // Initial fetch of security and simulation state
    api.getSecurityStatus().then((status) => {
      setSimulationMode(status.simulation_mode);
      setTokenStatus(status.status);
      setRateLimit({
        remaining: status.rate_limits.remaining,
        limit: status.rate_limits.limit_per_minute,
      });
    }).catch(() => {
      // Fallback
    });

    api.setRateLimitListener((remaining, limit) => {
      setRateLimit({ remaining, limit });
    });
  }, []);

  const handleToggle = async () => {
    try {
      const next = !simulationMode;
      await api.setSimulationMode(next);
      setSimulationMode(next);
    } catch (err: any) {
      alert(`Failed to toggle simulation mode: ${err.message}`);
    }
  };

  return (
    <div id="simulation-banner" className="w-full bg-gradient-to-r from-amber-950 via-amber-900 to-amber-950 border-b border-amber-500/40 px-4 py-2 text-amber-200 text-xs shadow-lg">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-2">
          <div className="flex items-center px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-bold tracking-wider text-[11px] border border-amber-400/40 animate-pulse">
            <AlertTriangle className="w-3.5 h-3.5 mr-1 text-amber-400" />
            SIMULATION MODE {simulationMode ? 'ACTIVE' : 'STANDBY'}
          </div>
          <span className="text-amber-200/90 font-medium hidden md:inline">
            All connector runs execute against local mock/sandboxed platforms. Mock runs are strictly labeled <span className="font-mono bg-black/30 px-1 py-0.5 rounded text-amber-300">mock</span> and cannot grant real-certified tiers.
          </span>
        </div>

        <div className="flex items-center space-x-4">
          {/* Rate Limit Badge */}
          <div className="flex items-center space-x-1 font-mono text-[11px] bg-black/40 px-2.5 py-1 rounded border border-amber-500/30">
            <Zap className="w-3 h-3 text-amber-400" />
            <span>Rate Limit:</span>
            <span className={rateLimit.remaining < 20 ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>
              {rateLimit.remaining}/{rateLimit.limit} req/min
            </span>
          </div>

          {/* Token Status Badge */}
          <div className="flex items-center space-x-1 font-mono text-[11px] bg-black/40 px-2.5 py-1 rounded border border-amber-500/30">
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
            <span>Token:</span>
            <span className={tokenStatus === 'active' ? 'text-emerald-400 font-semibold' : 'text-red-400 font-semibold'}>
              {tokenStatus.toUpperCase()}
            </span>
          </div>

          {/* Interactive Toggle */}
          <button
            onClick={handleToggle}
            id="toggle-simulation-mode-btn"
            title="Toggle simulation mode"
            className="flex items-center space-x-1 bg-amber-800/60 hover:bg-amber-700/80 text-amber-100 px-2 py-1 rounded text-[11px] transition border border-amber-500/40"
          >
            {simulationMode ? (
              <>
                <ToggleRight className="w-4 h-4 text-amber-300" />
                <span>Sim: ON</span>
              </>
            ) : (
              <>
                <ToggleLeft className="w-4 h-4 text-gray-400" />
                <span>Sim: OFF</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
