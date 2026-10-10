import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient } from '../api/client';
import { Navbar } from '../components/Navbar';

describe('Navbar', () => {
  beforeEach(() => {
    vi.spyOn(apiClient, 'getHealth').mockResolvedValue({
      status: 'healthy',
      app: 'News Sentiment Analyzer',
      version: '0.1.0',
      environment: 'testing',
      database: 'connected',
      models_loaded: ['vader'],
    });
  });

  it('renders application branding and all 5 navigation tabs', async () => {
    const handleTabChange = vi.fn();
    render(<Navbar activeTab="topic" onTabChange={handleTabChange} />);

    expect(screen.getByText('News Sentiment Analyzer')).toBeInTheDocument();
    expect(screen.getByText('Topic Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Headline Detail')).toBeInTheDocument();
    expect(screen.getByText('Try It Live')).toBeInTheDocument();
    expect(screen.getByText('Model Comparison')).toBeInTheDocument();
    expect(screen.getByText('Research Results')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('API Connected')).toBeInTheDocument();
    });
  });

  it('triggers onTabChange when a tab is clicked', async () => {
    const handleTabChange = vi.fn();
    render(<Navbar activeTab="topic" onTabChange={handleTabChange} />);

    fireEvent.click(screen.getByText('Try It Live'));
    expect(handleTabChange).toHaveBeenCalledWith('try-it');

    fireEvent.click(screen.getByText('Research Results'));
    expect(handleTabChange).toHaveBeenCalledWith('results');

    await waitFor(() => {
      expect(screen.getByText('API Connected')).toBeInTheDocument();
    });
  });
});
