import React, { useState } from 'react';
import { SimulationBanner } from './components/SimulationBanner';
import { Sidebar, PageId } from './components/Sidebar';
import { OverviewPage } from './pages/OverviewPage';
import { DestinationsPage } from './pages/DestinationsPage';
import { ConnectorsPage } from './pages/ConnectorsPage';
import { PublishPage } from './pages/PublishPage';
import { RulesPage } from './pages/RulesPage';
import { CertificationPage } from './pages/CertificationPage';
import { CatalogueImportPage } from './pages/CatalogueImportPage';
import { JobsPage } from './pages/JobsPage';
import { SettingsPage } from './pages/SettingsPage';
import { Radio, ShieldCheck } from 'lucide-react';
import { api } from './api/client';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageId>('overview');
  const [targetDestinationId, setTargetDestinationId] = useState<string | undefined>(undefined);

  const handleNavigateToCertify = (destinationId: string) => {
    setTargetDestinationId(destinationId);
    setCurrentPage('certification');
  };

  const handleNavigateToPublish = (destinationId: string) => {
    setTargetDestinationId(destinationId);
    setCurrentPage('publish');
  };

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'overview':
        return <OverviewPage onNavigate={(p) => setCurrentPage(p)} />;
      case 'destinations':
        return (
          <DestinationsPage
            onNavigateToCertify={handleNavigateToCertify}
            onNavigateToPublish={handleNavigateToPublish}
          />
        );
      case 'connectors':
        return <ConnectorsPage />;
      case 'publish':
        return <PublishPage initialDestinationId={targetDestinationId} />;
      case 'rules':
        return <RulesPage />;
      case 'certification':
        return <CertificationPage initialDestinationId={targetDestinationId} />;
      case 'import':
        return <CatalogueImportPage />;
      case 'jobs':
        return <JobsPage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <OverviewPage onNavigate={(p) => setCurrentPage(p)} />;
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-100 flex flex-col font-sans">
      {/* 1. Top Simulation Mode Banner (Always Visible) */}
      <SimulationBanner />

      {/* 2. Main Workspace Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar currentPage={currentPage} onSelectPage={(p) => setCurrentPage(p)} />

        {/* Right Content Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
          {/* Top Bar */}
          <header className="h-14 bg-[#0d121f]/80 backdrop-blur-md border-b border-gray-800 px-6 flex items-center justify-between shrink-0">
            <div className="flex items-center space-x-2">
              <span className="text-xs uppercase font-mono tracking-wider text-gray-400">Control Plane /</span>
              <span className="text-xs uppercase font-mono font-bold text-sky-400 capitalize">{currentPage}</span>
            </div>

            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-1.5 text-xs text-gray-300 font-mono bg-gray-900 px-2.5 py-1 rounded-md border border-gray-800">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-gray-400">Token:</span>
                <span className="text-emerald-400 font-bold truncate max-w-[120px]">
                  {api.getToken().substring(0, 12)}...
                </span>
              </div>

              <div className="flex items-center space-x-1.5 text-xs text-emerald-400 font-mono bg-emerald-950/30 px-2.5 py-1 rounded-md border border-emerald-500/30">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className="font-semibold">ENGINE LIVE</span>
              </div>
            </div>
          </header>

          {/* Page Body */}
          <main className="flex-1 p-6 max-w-7xl w-full mx-auto animate-in fade-in duration-200">
            {renderCurrentPage()}
          </main>
        </div>
      </div>
    </div>
  );
};

export default App;
