import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom/vitest';
import Governance from './Governance';
import Innovation from './Innovation';
import { api } from '../api/client';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe('Risk and innovation views', () => {
  it('shows loading and absent risk data', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: { latest: null } });
    render(<Governance />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading');
    expect(await screen.findByText('No risk assessment available.')).toBeInTheDocument();
  });

  it('renders the supplied risk assessment and missing field', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: { latest: { recorded_date: '2025-01-01', updated_at: '2025-01-02', compliance_pct: '0.00', nist_maturity: 'Tier 3', privacy_audit_status: null } } });
    render(<Governance />);
    expect(await screen.findByText('0.00%')).toBeInTheDocument();
    expect(screen.getByText('Tier 3')).toBeInTheDocument();
    expect(within(screen.getByRole('heading', { name: 'Data Privacy Audit Status' }).parentElement).getByText('Not provided')).toBeInTheDocument();
  });

  it('renders empty innovation sections and retries a failure', async () => {
    vi.spyOn(api, 'get').mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ data: { latest: null, portfolio: [] } });
    render(<Innovation />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('No innovation outcomes available.')).toBeInTheDocument();
    expect(screen.getByText('No innovation portfolio available.')).toBeInTheDocument();
  });

  it('renders outcome zero and supplied portfolio values with their period and unit', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: {
      latest: { year: 2025, quarter: 1, deployed_models: 0, patent_disclosures: null, innovation_index: '64.25', updated_at: 'today' },
      portfolio: [{ year: 2025, quarter: 2, category: 'GenAI', amount: '12.50', unit: 'USD M', updated_at: 'today' }],
    } });
    render(<Innovation />);
    expect(await screen.findByText('64.25')).toBeInTheDocument();
    expect(within(screen.getByRole('heading', { name: 'AI models deployed to production' }).parentElement).getByText('0')).toBeInTheDocument();
    expect(screen.getByRole('row', { name: /GenAI 12.50 USD M/ })).toBeInTheDocument();
    expect(screen.getByText(/Reporting period: Q1 2025/)).toBeInTheDocument();
    expect(screen.getByText(/Source-reported portfolio · Q2 2025/)).toBeInTheDocument();
    expect(screen.getByText('Not provided')).toBeInTheDocument();
  });

  it('reports risk request errors and recovers on retry', async () => {
    vi.spyOn(api, 'get').mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ data: { latest: null } });
    render(<Governance />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('No risk assessment available.')).toBeInTheDocument();
  });
});
