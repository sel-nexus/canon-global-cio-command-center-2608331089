import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom/vitest';
import Assistant from './Assistant';
import { api } from '../api/client';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it('launches a contextual recommendation, renders provider output and restores focus', async () => {
  vi.spyOn(api, 'get').mockResolvedValue({ data: [{ label: 'Review', query: 'Review data', context_tab: 'strategic' }] });
  vi.spyOn(api, 'post').mockResolvedValue({ data: { narrative: 'Reported analysis', actions: ['Investigate'], confidence: null, limitations: ['Verify evidence'] } });
  render(<Assistant tab="strategic" launch={null} onLaunchHandled={() => {}} />);
  await userEvent.click(await screen.findByRole('button', { name: 'Review' }));
  expect(await screen.findByText('Reported analysis')).toBeInTheDocument();
  expect(screen.getByText('Confidence: Not supplied')).toBeInTheDocument();
  expect(screen.getByText('Verify evidence')).toBeInTheDocument();
  expect(api.post).toHaveBeenCalledWith('/ai/chat', { query: 'Review data', context_tab: 'strategic' });
  await userEvent.keyboard('{Escape}');
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Review' })).toHaveFocus();
});

it('shows provider failure, supports retry and refreshes context on tab change', async () => {
  vi.spyOn(api, 'get').mockImplementation((path, config) => Promise.resolve({ data: [{ label: config.params.context_tab, query: 'Review', context_tab: config.params.context_tab }] }));
  vi.spyOn(api, 'post').mockRejectedValueOnce({ response: { data: { detail: 'AI provider is not configured or approved.' } } }).mockResolvedValue({ data: { narrative: 'Done', actions: [], confidence: 'Low', limitations: [] } });
  const { rerender } = render(<Assistant tab="operations" launch={null} onLaunchHandled={() => {}} />);
  await userEvent.click(screen.getByRole('button', { name: 'Executive assistant' }));
  await userEvent.type(screen.getByLabelText('Your question'), 'What changed?');
  await userEvent.click(screen.getByRole('button', { name: 'Ask assistant' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('not configured');
  await userEvent.click(screen.getByRole('button', { name: 'Ask assistant' }));
  expect(await screen.findByText('Done')).toBeInTheDocument();
  rerender(<Assistant tab="business" launch={null} onLaunchHandled={() => {}} />);
  await waitFor(() => expect(api.get).toHaveBeenLastCalledWith('/ai/recommendations', { params: { context_tab: 'business' } }));
  expect(screen.queryByText('Done')).not.toBeInTheDocument();
});

it('opens and sends the partnership summary request', async () => {
  vi.spyOn(api, 'get').mockResolvedValue({ data: [] });
  vi.spyOn(api, 'post').mockResolvedValue({ data: { narrative: 'Summary', actions: [], confidence: null, limitations: [] } });
  const handled = vi.fn();
  render(<Assistant tab="partnerships" launch={{ tab: 'partnerships', query: 'Summarize partnerships' }} onLaunchHandled={handled} />);
  expect(await screen.findByText('Summary')).toBeInTheDocument();
  expect(api.post).toHaveBeenCalledWith('/ai/chat', { query: 'Summarize partnerships', context_tab: 'partnerships' });
  expect(handled).toHaveBeenCalled();
});
