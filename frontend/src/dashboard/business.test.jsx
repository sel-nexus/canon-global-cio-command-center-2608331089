import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom/vitest';
import Business from './Business';
import { api } from '../api/client';

vi.mock('react-chartjs-2', () => ({ Bar: ({ 'aria-label': label, data, options }) => <div role="img" aria-label={label} data-chart={JSON.stringify({ data, options })} /> }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const row = { year: 2025, quarter: 2, investment_m: '10.50', revenue_attribution_m: '19.25', cost_avoidance_m: '3.00', operational_cost_savings_m: '2.00', transformation_roi_pct: '-5.25', updated_at: '2025-07-01T00:00:00Z' };

describe('Business impact', () => {
  it('shows loading and empty states', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: { quarters: [], total: 0 } });
    render(<Business />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading');
    expect(await screen.findByText('No business impact data available.')).toBeInTheDocument();
  });

  it('shows reported cards, chart values, and missing values without substitutions', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: { quarters: [{ ...row, quarter: 1, revenue_attribution_m: null }, row], total: 3 } });
    render(<Business />);
    const chart = await screen.findByRole('img', { name: 'Quarterly business impact comparison' });
    const chartProps = JSON.parse(chart.dataset.chart);
    expect(chartProps.data.datasets.map((series) => series.data[1])).toEqual([10.5, 19.25, 3]);
    expect(chartProps.data.datasets[1].data[0]).toBeNull();
    expect(chartProps.options.scales.x.stacked).toBe(true);
    expect(screen.getByText('-5.25%')).toBeInTheDocument();
    expect(screen.getByText('2.00')).toBeInTheDocument();
    expect(within(screen.getByRole('row', { name: /Q1 2025/ })).getByText('Not provided')).toBeInTheDocument();
    expect(screen.getByText('Showing the latest 2 of 3 quarters.')).toBeInTheDocument();
  });

  it('does not replace missing latest ROI or savings with older data', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: { quarters: [row, { ...row, quarter: 3, operational_cost_savings_m: null, transformation_roi_pct: null }], total: 2 } });
    render(<Business />);
    await screen.findByText(/Value cards: Q3 2025/);
    expect(screen.getAllByText('Not provided')).toHaveLength(2);
    expect(screen.queryByText('-5.25%')).not.toBeInTheDocument();
  });

  it('reports errors and can retry', async () => {
    vi.spyOn(api, 'get').mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ data: { quarters: [], total: 0 } });
    render(<Business />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load');
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('No business impact data available.')).toBeInTheDocument();
  });
});
