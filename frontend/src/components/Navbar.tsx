import React, { useEffect, useState } from 'react';
import { BarChart3, Search, Zap, Scale, Award, Activity, Radio } from 'lucide-react';
import { apiClient } from '../api/client';
import type { HealthResponse } from '../api/types';

export type NavTab = 'topic' | 'detail' | 'try-it' | 'comparison' | 'results';

interface NavbarProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, onTabChange }) => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isOnline, setIsOnline] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    const checkHealth = async () => {
      try {
        const data = await apiClient.getHealth();
        if (isMounted) {
          setHealth(data);
          setIsOnline(data.status === 'healthy' || data.status === 'degraded');
        }
      } catch {
        if (isMounted) {
          setIsOnline(false);
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const navItems: { id: NavTab; label: string; icon: React.ReactNode }[] = [
    { id: 'topic', label: 'Topic Dashboard', icon: <BarChart3 size={16} /> },
    { id: 'detail', label: 'Headline Detail', icon: <Search size={16} /> },
    { id: 'try-it', label: 'Try It Live', icon: <Zap size={16} /> },
    { id: 'comparison', label: 'Model Comparison', icon: <Scale size={16} /> },
    { id: 'results', label: 'Research Results', icon: <Award size={16} /> },
  ];

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        backgroundColor: 'rgba(8, 12, 21, 0.85)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--border-card)',
        padding: '0 24px',
      }}
    >
      <div
        style={{
          maxWidth: '1440px',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          height: '68px',
          gap: '20px',
        }}
      >
        {/* Brand Logo & Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, #0284c7 0%, #6366f1 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 16px rgba(56, 189, 248, 0.35)',
            }}
          >
            <Activity size={20} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: '18px',
                  fontWeight: 800,
                  color: '#ffffff',
                  letterSpacing: '-0.02em',
                }}
              >
                News Sentiment Analyzer
              </span>
              <span
                style={{
                  fontSize: '10px',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--accent-cyan)',
                  backgroundColor: 'rgba(56, 189, 248, 0.1)',
                  padding: '2px 6px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid rgba(56, 189, 248, 0.25)',
                }}
              >
                v{health?.version || '0.1.0'}
              </span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Multi-Model Inference & Faithfulness Intelligence
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            padding: '4px',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onTabChange(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 14px',
                  fontSize: '13px',
                  fontWeight: 600,
                  borderRadius: 'var(--radius-md)',
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)',
                  backgroundColor: isActive ? 'var(--accent-cyan-glow)' : 'transparent',
                  color: isActive ? '#ffffff' : 'var(--text-secondary)',
                  boxShadow: isActive ? '0 0 12px rgba(56, 189, 248, 0.2)' : 'none',
                }}
              >
                <span style={{ color: isActive ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Backend Liveness Status Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: 'var(--radius-full)',
              backgroundColor: isOnline ? 'rgba(16, 185, 129, 0.12)' : 'rgba(244, 63, 94, 0.12)',
              border: `1px solid ${
                isOnline ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'
              }`,
              fontSize: '12px',
              fontWeight: 500,
            }}
            title={
              isOnline
                ? `API Online (${health?.models_loaded?.length || 1} models preloaded)`
                : 'API Offline or Unreachable'
            }
          >
            <Radio
              size={14}
              style={{
                color: isOnline ? 'var(--sentiment-pos)' : 'var(--sentiment-neg)',
                animation: isOnline ? 'pulse 2s infinite' : 'none',
              }}
            />
            <span
              style={{
                color: isOnline ? 'var(--sentiment-pos)' : 'var(--sentiment-neg)',
                fontSize: '12px',
              }}
            >
              {isOnline ? 'API Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
