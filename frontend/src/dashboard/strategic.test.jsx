import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom/vitest';
import Strategic from './Strategic';
import { api } from '../api/client';

vi.mock('react-chartjs-2', () => ({ Line: ({ 'aria-label': label }) => <div role="img" aria-label={label} />, Bar: ({ 'aria-label': label }) => <div role="img" aria-label={label} /> }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const empty = { window_start: '2024-02-01', window_end: '2025-01-15', metrics: [], trends: [], budgets: [], insights: [] };

describe('Strategic dashboard', () => {
  it('shows loading then the empty state', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: empty });
    render(<Strategic />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading');
    expect(await screen.findByText(/No strategic data available/)).toBeInTheDocument();
  });
  it('renders persisted observations, insight, comparisons and charts', async () => {
    const metric = { category: 'business', metric_name: 'Impact', metric_value: '20.00', unit: 'USD', trend: 'up', change_pct: '5.00', insight: 'Improved', recorded_date: '2025-01-01' };
    vi.spyOn(api, 'get').mockResolvedValue({ data: { ...empty, metrics: [metric], trends: [metric], insights: [metric], budgets: [{ name: 'IT', month: '2025-01-01', unit: 'USD', budget: '50.00', actual: '40.00' }] } });
    render(<Strategic />);
    expect(await screen.findAllByText('20.00 USD')).toHaveLength(2);
    expect(screen.getByText(/Improved/)).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Impact performance chart' })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'IT budget versus actual chart' })).toBeInTheDocument();
    expect(screen.getByText('40.00')).toBeInTheDocument();
  });
  it('retries a failed request and displays export failures', async () => {
    const get = vi.spyOn(api, 'get').mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ data: empty }).mockRejectedValueOnce(new Error('export failed'));
    render(<Strategic />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load');
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText(/No strategic data available/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Export CSV' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Export failed');
    expect(get).toHaveBeenLastCalledWith('/dashboard/strategic-metrics/export', expect.objectContaining({ params: { format: 'csv' } }));
  });
});
