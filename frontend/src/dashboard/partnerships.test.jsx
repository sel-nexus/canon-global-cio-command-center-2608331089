import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom/vitest';
import Partnerships from './Partnerships';
import { api } from '../api/client';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const partner = {
  id: 1, vendor_name: 'Supplier A', sla_compliance_pct: '98.25', delivery_score: '88.50',
  innovation_output: 'Two pilots', annual_spend: '1234.50', currency: 'USD', roi_multiple: '1.25',
  contract_status: 'Review', review_quarter: '2025 Q2', updated_at: '2025-07-01', history_total: 3,
  history: [{ year: 2025, quarter: 1, currency: 'EUR', spend: '0.00', verified_savings: null, roi_multiple: '-0.25' },
    { year: 2025, quarter: 2, currency: 'USD', spend: '15.00', verified_savings: '50.00', roi_multiple: null }],
};

describe('Partnerships', () => {
  it('shows loading and an honest empty state', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: { partners: [], total: 0 } });
    render(<Partnerships />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading');
    expect(await screen.findByText('No partnership data available.')).toBeInTheDocument();
  });

  it('renders current assessment and ordered source values including nulls', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: { partners: [partner], total: 1 } });
    render(<Partnerships />);
    expect(await screen.findByRole('heading', { name: 'Supplier A' })).toBeInTheDocument();
    expect(screen.getByText('98.25%')).toBeInTheDocument();
    expect(screen.getByText('Two pilots')).toBeInTheDocument();
    expect(screen.getByText('USD 1234.50')).toBeInTheDocument();
    const first = within(screen.getByRole('row', { name: /Q1 2025/ }));
    expect(first.getByText('0.00')).toBeInTheDocument();
    expect(first.getByText('EUR')).toBeInTheDocument();
    expect(first.getByText('Not provided')).toBeInTheDocument();
    expect(first.getByText('-0.25×')).toBeInTheDocument();
    expect(screen.getByText('Showing the latest 2 of 3 quarters.')).toBeInTheDocument();
  });

  it('shows missing history and supports pagination', async () => {
    vi.spyOn(api, 'get').mockResolvedValueOnce({ data: { partners: [{ ...partner, history: [], history_total: 0 }], total: 21 } })
      .mockResolvedValueOnce({ data: { partners: [{ ...partner, vendor_name: 'Supplier B' }], total: 21 } });
    render(<Partnerships />);
    expect(await screen.findByText('No quarterly history available.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Next partners' }));
    expect(await screen.findByRole('heading', { name: 'Supplier B' })).toBeInTheDocument();
    expect(api.get).toHaveBeenLastCalledWith('/partnerships?limit=20&offset=20');
  });

  it('reports request errors and retries', async () => {
    vi.spyOn(api, 'get').mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ data: { partners: [], total: 0 } });
    render(<Partnerships />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load');
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('No partnership data available.')).toBeInTheDocument();
  });
});
