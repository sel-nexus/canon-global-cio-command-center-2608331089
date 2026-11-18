import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';
import Regional from './Regional';
import { api } from '../api/client';

vi.mock('react-chartjs-2', () => ({ Radar: ({ 'aria-label': label }) => <div role="img" aria-label={label} /> }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const row = { region: 'EMEA', health_score: '68.25', availability_pct: '99.70', security_score: '73.10', transformation_index: '54.50', status: 'Warning', updated_at: '2025-01-01T00:00:00Z' };
const mount = () => render(<MemoryRouter><Regional /></MemoryRouter>);

describe('Regional dashboard', () => {
  it('shows loading and explicit empty states', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: { regions: [] } });
    mount();
    expect(screen.getByRole('status')).toHaveTextContent('Loading');
    expect(await screen.findByText('No regional radar data available.')).toBeInTheDocument();
    expect(screen.getByText('No regional performance data available.')).toBeInTheDocument();
  });
  it('shows source scores and investigates warning regions', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: { regions: [row] } });
    mount();
    expect(await screen.findByRole('img', { name: 'Regional health radar comparison' })).toBeInTheDocument();
    expect(screen.getByText('99.70%')).toBeInTheDocument();
    expect(screen.getByText('Warning')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Investigate EMEA' }));
    expect(screen.getByRole('heading', { name: 'Investigate EMEA' })).toBeInTheDocument();
    expect(screen.getByText(/Causes, thresholds/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Close investigation' }));
    expect(screen.queryByRole('heading', { name: 'Investigate EMEA' })).not.toBeInTheDocument();
  });
  it('reports request failures and retries both endpoints', async () => {
    const get = vi.spyOn(api, 'get').mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ data: { regions: [] } });
    mount();
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load');
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('No regional performance data available.')).toBeInTheDocument();
    expect(get).toHaveBeenCalledTimes(4);
  });
});
