import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom/vitest';
import Assistant from './Assistant';
import { api } from '../api/client';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it('launches a contextual recommendation, renders provider output and restores focus', async () => {
  vi.spyOn(api, 'get').mockResolvedValue({ data: [{ label: 'Review', query: 'Review data', context_tab: 'strategic' }] });
  vi.spyOn(api, 'post').mockResolvedValue({ data: { source: 'provider', narrative: 'Reported analysis', actions: ['Investigate'], confidence: null, limitations: ['Verify evidence'] } });
  render(<Assistant tab="strategic" launch={null} onLaunchHandled={() => {}} />);
  await userEvent.click(await screen.findByRole('button', { name: 'Review' }));
  expect(await screen.findByText('Reported analysis')).toBeInTheDocument();
  expect(screen.getByText('Source: AI provider')).toBeInTheDocument();
  expect(screen.queryByText(/MOCK \/ synthetic output/)).not.toBeInTheDocument();
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

it('wraps keyboard focus within the assistant drawer in both directions', async () => {
  const user = userEvent.setup();
  vi.spyOn(api, 'get').mockResolvedValue({ data: [] });
  render(<Assistant tab="business" launch={null} onLaunchHandled={() => {}} />);
  const trigger = screen.getByRole('button', { name: 'Executive assistant' });
  await user.click(trigger);
  const close = screen.getByRole('button', { name: 'Close assistant' });
  const question = screen.getByLabelText('Your question');
  expect(close).toHaveFocus();
  // The empty form's submit button is disabled and must not enter the focus loop.
  await user.tab({ shift: true });
  expect(question).toHaveFocus();
  await user.tab();
  expect(close).toHaveFocus();
  await user.tab();
  expect(question).toHaveFocus();
  await user.type(question, 'Review');
  const submit = screen.getByRole('button', { name: 'Ask assistant' });
  await user.tab();
  expect(submit).toHaveFocus();
  await user.tab();
  expect(close).toHaveFocus();
  await user.tab({ shift: true });
  expect(submit).toHaveFocus();
  await user.keyboard('{Escape}');
  expect(trigger).toHaveFocus();
});

it.each(['resolve', 'reject'])('ignores a stale chat %s after the tab changes and preserves the newer result', async (settlement) => {
  const user = userEvent.setup();
  vi.spyOn(api, 'get').mockResolvedValue({ data: [] });
  let resolveOld;
  let rejectOld;
  const oldRequest = new Promise((resolve, reject) => { resolveOld = resolve; rejectOld = reject; });
  vi.spyOn(api, 'post').mockReturnValueOnce(oldRequest).mockResolvedValueOnce({ data: { narrative: 'Current analysis', actions: [], confidence: null, limitations: [] } });
  const { rerender } = render(<Assistant tab="strategic" launch={null} onLaunchHandled={() => {}} />);
  await user.click(screen.getByRole('button', { name: 'Executive assistant' }));
  await user.type(screen.getByLabelText('Your question'), 'First question');
  await user.click(screen.getByRole('button', { name: 'Ask assistant' }));
  expect(screen.getByRole('status')).toHaveTextContent('Waiting for assistant response');
  rerender(<Assistant tab="business" launch={null} onLaunchHandled={() => {}} />);
  await user.clear(screen.getByLabelText('Your question'));
  await user.type(screen.getByLabelText('Your question'), 'Second question');
  await user.click(screen.getByRole('button', { name: 'Ask assistant' }));
  expect(await screen.findByText('Current analysis')).toBeInTheDocument();
  expect(api.post).toHaveBeenLastCalledWith('/ai/chat', { query: 'Second question', context_tab: 'business' });
  await act(async () => {
    if (settlement === 'resolve') resolveOld({ data: { narrative: 'Stale analysis', actions: [], confidence: null, limitations: [] } });
    else rejectOld({ response: { data: { detail: 'Stale failure' } } });
    await oldRequest.catch(() => {});
  });
  expect(screen.getByText('Current analysis')).toBeInTheDocument();
  expect(screen.queryByText('Stale analysis')).not.toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});

it('labels synthetic output and removes it on tab change and error', async () => {
  const user = userEvent.setup();
  vi.spyOn(api, 'get').mockResolvedValue({ data: [] });
  vi.spyOn(api, 'post').mockResolvedValueOnce({ data: {
    source: 'mock', narrative: 'MOCK / synthetic example', actions: ['MOCK / synthetic action'],
    confidence: 'MOCK / synthetic: not assessed', limitations: ['Not for decisions'],
  } }).mockRejectedValueOnce({ response: { data: { detail: 'Unavailable' } } });
  const { rerender } = render(<Assistant tab="strategic" launch={null} onLaunchHandled={() => {}} />);
  await user.click(screen.getByRole('button', { name: 'Executive assistant' }));
  await user.type(screen.getByLabelText('Your question'), 'Review');
  await user.click(screen.getByRole('button', { name: 'Ask assistant' }));
  expect(await screen.findByText('MOCK / synthetic output — not an analysis of dashboard data.')).toBeInTheDocument();
  expect(screen.getByText('MOCK / synthetic action')).toBeInTheDocument();
  expect(screen.getByText('Confidence: MOCK / synthetic: not assessed')).toBeInTheDocument();
  rerender(<Assistant tab="business" launch={null} onLaunchHandled={() => {}} />);
  expect(screen.queryByText(/MOCK \/ synthetic output/)).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Ask assistant' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Unavailable');
  expect(screen.queryByText(/MOCK \/ synthetic output/)).not.toBeInTheDocument();
});

it('ignores stale recommendation responses when changing tabs', async () => {
  let resolveOld;
  const oldRequest = new Promise((resolve) => { resolveOld = resolve; });
  vi.spyOn(api, 'get').mockReturnValueOnce(oldRequest).mockResolvedValueOnce({ data: [{ label: 'Business prompt', query: 'Business question', context_tab: 'business' }] });
  const { rerender } = render(<Assistant tab="strategic" launch={null} onLaunchHandled={() => {}} />);
  rerender(<Assistant tab="business" launch={null} onLaunchHandled={() => {}} />);
  await userEvent.click(screen.getByRole('button', { name: 'Executive assistant' }));
  expect(await screen.findByRole('button', { name: 'Business prompt' })).toBeInTheDocument();
  await act(async () => {
    resolveOld({ data: [{ label: 'Old prompt', query: 'Old question', context_tab: 'strategic' }] });
    await oldRequest;
  });
  expect(screen.getByRole('button', { name: 'Business prompt' })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Old prompt' })).not.toBeInTheDocument();
});
