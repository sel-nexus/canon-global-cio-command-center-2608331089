import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom/vitest';
import Operations from './Operations';
import { api } from '../api/client';

vi.mock('react-chartjs-2', () => ({ Line: ({ 'aria-label': label, data, options }) => <div role="img" aria-label={label} data-chart={JSON.stringify({ data, options })} /> }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const empty = { active_counts: null, latest: null, history: [], history_total: 0 };
const incidents = { incidents: [], total: 0 };
const row = { recorded_date: '2025-01-01', mttr_minutes: '12.50', sla_compliance_pct: '99.50', uptime_pct: '99.99', incident_volume: 4, resolution_count: 2, p1_volume: 1, p2_volume: null, updated_at: '2025-01-02T00:00:00Z' };

describe('Operations', () => {
  it('shows loading and honest empty states', async () => {
    vi.spyOn(api, 'get').mockImplementation((url) => Promise.resolve({ data: url.endsWith('summary') ? empty : incidents }));
    render(<Operations />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading');
    expect(await screen.findByText('No incidents available.')).toBeInTheDocument();
    expect(screen.getByText('No incident history available.')).toBeInTheDocument();
    expect(within(screen.getByRole('heading', { name: 'Active P1' }).parentElement).getByText('Not provided')).toBeInTheDocument();
  });

  it('shows source values, missing values, severity counts and both chart axes', async () => {
    const summary = { active_counts: { P1: 1, P2: 0, P3: 2 }, latest: row, history: [row], history_total: 1 };
    const list = { incidents: [{ incident_number: 'I1', title: 'Network', severity: 'P1', status: 'Open', created_at: '2025-01-01', resolved_at: null }], total: 1 };
    vi.spyOn(api, 'get').mockImplementation((url) => Promise.resolve({ data: url.endsWith('summary') ? summary : list }));
    render(<Operations />);
    const chart = await screen.findByRole('img', { name: 'Incident volume and resolution history' });
    const props = JSON.parse(chart.dataset.chart);
    expect(props.data.datasets.map((series) => series.data[0])).toEqual([4, 1, null, 2]);
    expect(props.data.datasets[3].yAxisID).toBe('resolutions');
    expect(props.options.scales.resolutions.position).toBe('right');
    expect(screen.getByText('12.50')).toBeInTheDocument();
    expect(screen.getByText('99.50%')).toBeInTheDocument();
    expect(screen.getByText('99.99%')).toBeInTheDocument();
    expect(screen.getByRole('row', { name: /I1 Network P1 Open/ })).toBeInTheDocument();
    expect(within(screen.getByRole('row', { name: /2025-01-01 4 1/ })).getByText('Not provided')).toBeInTheDocument();
  });

  it('reports either request failing and retries', async () => {
    vi.spyOn(api, 'get').mockImplementationOnce(() => Promise.reject(new Error('offline'))).mockImplementation((url) => Promise.resolve({ data: url.endsWith('summary') ? empty : incidents }));
    render(<Operations />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load');
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('No incidents available.')).toBeInTheDocument();
  });
});
