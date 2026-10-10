import React, { useState, useEffect } from 'react';
import type { HeadlineItem } from './api/types';
import { Navbar, type NavTab } from './components/Navbar';
import { HeadlineDetail } from './pages/HeadlineDetail';
import { ModelComparison } from './pages/ModelComparison';
import { Results } from './pages/Results';
import { TopicDashboard } from './pages/TopicDashboard';
import { TryIt } from './pages/TryIt';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('topic');
  const [selectedHeadline, setSelectedHeadline] = useState<HeadlineItem | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('vader');

  // URL hash synchronization for bookmarking and history support
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '') as NavTab;
      if (['topic', 'detail', 'try-it', 'comparison', 'results'].includes(hash)) {
        setActiveTab(hash);
      }
    };

    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleTabChange = (tab: NavTab) => {
    setActiveTab(tab);
    window.location.hash = tab;
  };

  const handleSelectHeadline = (headline: HeadlineItem, modelName: string) => {
    setSelectedHeadline(headline);
    setSelectedModel(modelName);
    handleTabChange('detail');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Top Sticky Header */}
      <Navbar activeTab={activeTab} onTabChange={handleTabChange} />

      {/* Main Content Area */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {activeTab === 'topic' && <TopicDashboard onSelectHeadline={handleSelectHeadline} />}
        {activeTab === 'detail' && (
          <HeadlineDetail
            headline={selectedHeadline}
            initialModel={selectedModel}
            onBack={() => handleTabChange('topic')}
          />
        )}
        {activeTab === 'try-it' && <TryIt />}
        {activeTab === 'comparison' && <ModelComparison onSelectHeadline={handleSelectHeadline} />}
        {activeTab === 'results' && <Results />}
      </main>

      {/* Footer */}
      <footer
        style={{
          borderTop: '1px solid var(--border-card)',
          backgroundColor: 'rgba(8, 12, 21, 0.95)',
          padding: '24px',
          marginTop: 'auto',
          fontSize: '13px',
          color: 'var(--text-muted)',
        }}
      >
        <div
          style={{
            maxWidth: '1440px',
            margin: '0 auto',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '16px',
          }}
        >
          <div>
            <span style={{ fontWeight: 600, color: '#ffffff' }}>News Sentiment Analyzer</span> —
            Empirical Benchmark & Explainability Intelligence Dashboard
          </div>

          <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
            <a href="/docs" target="_blank" rel="noopener noreferrer">
              OpenAPI Swagger Docs
            </a>
            <a href="/api/v1/models" target="_blank" rel="noopener noreferrer">
              Model Registry JSON
            </a>
            <a href="/api/v1/health" target="_blank" rel="noopener noreferrer">
              System Health
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
